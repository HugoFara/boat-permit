"""Ingest French navigation law from the official DILA **LEGI** open data.

France's analogue of the Swiss Fedlex pipeline (`src/parsers/akn.py`): it turns
the statutes the question bank cites into article-level `KnowledgeUnit`s, so the
bank is **grounded in and verified against the actual text** rather than recall.

Source: the LEGI dataset, published by the DILA as structured XML under the
**Licence Ouverte / Etalab** — freely reusable. We read the bulk
`Freemium_legi_global_*.tar.gz` dump (no API credentials). It carries both the
consolidated **codes** (`code_en_vigueur`) and the non-codified **lois/décrets/
arrêtés** (`TNC_en_vigueur/JORF`), so one dump covers every French source below.
Each in-force article is one XML file under its text's own `article/` subtree,
filterable by id and `<NUM>`.

Ingested texts (`TEXTS`):
  - Code des transports, 4ᵉ partie (navigation intérieure = the RGP)
  - Code de l'environnement, art. L.218-x (rejets des navires / MARPOL)
  - Décret n° 2007-1167 (permis plaisance) ; Arrêté du 28 sept. 2007 (référentiel)
  - Arrêté du 10 fév. 2016 (Division 245 — armement/sécurité eaux intérieures)
COLREG/RIPAM is ingested elsewhere (the `INT` layer); Division 240's annexed
tables are not cleanly in LEGI.

The durable artifact is the committed corpus `src/fr/legi_kb.json`; the 1.2 GB
dump + extracted tree stay under `data/raw/legi/` (git-ignored). Rebuild:

    python -m src.fr.legi extract   # dump -> data/raw/legi/ (needs the tar)
    python -m src.fr.legi build     # extracted articles -> KB + corpus JSON
    python -m src.fr.legi verify     # cross-check seed_fr citations vs the law
"""

from __future__ import annotations

import datetime as _dt
import glob
import os
import re
import subprocess
from dataclasses import dataclass

from lxml import etree

from ..schema import KnowledgeUnit, make_id, connect, write_units, set_meta, export_json
from . import themes_fr  # noqa: F401  — registers FR themes with the shared validator

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
LEGI_DIR = os.path.join(ROOT, "data", "raw", "legi")
DUMP = os.path.join(LEGI_DIR, "legi_global.tar.gz")
KB_DB = os.path.join(ROOT, "data", "kb.fr.sqlite")
KB_JSON = os.path.join(ROOT, "src", "fr", "legi_kb.json")   # committed corpus

_ETALAB = ("Licence Ouverte / Open Licence 2.0 (Etalab) — {name} (DILA, base LEGI), "
           "librement réutilisable.")
ART_URL = "https://www.legifrance.gouv.fr/codes/article_lc/{id}"
JORF_URL = "https://www.legifrance.gouv.fr/jorf/article_jo/{id}"


@dataclass(frozen=True)
class Text:
    """One statute to ingest. `key` is its LEGITEXT/JORFTEXT id (the dump path
    segment); `num` keeps only matching article numbers (None ⇒ all in-force, for
    short non-codified texts); `kind` picks the per-article URL builder."""
    source_id: str
    key: str
    name: str
    ref_prefix: str
    default_theme: str
    num: str | None = None
    kind: str = "code"           # "code" | "jorf"


TEXTS: list[Text] = [
    # Code des transports — 4ᵉ partie (navigation intérieure & transport fluvial).
    Text("code_transports", "LEGITEXT000023086525", "Code des transports",
         "Code des transports, art. ", "voies_navigables", num=r"^[LRAD]4\d{3}"),
    # Code de l'environnement — pollution par les rejets des navires (MARPOL).
    Text("code_environnement", "LEGITEXT000006074220", "Code de l'environnement",
         "Code de l'environnement, art. ", "environnement", num=r"^[LR]218-"),
    # Permis plaisance: the decree + the 28 Sept 2007 référentiel order.
    Text("decret_2007", "JORFTEXT000000648362",
         "Décret n° 2007-1167 du 2 août 2007 (permis plaisance)",
         "Décret 2007-1167, art. ", "reglementation", kind="jorf"),
    Text("arrete_2007", "JORFTEXT000000428843",
         "Arrêté du 28 septembre 2007 (permis plaisance — référentiel)",
         "Arrêté 28 sept. 2007, art. ", "reglementation", kind="jorf"),
    # Inland safety equipment.
    Text("division_245", "JORFTEXT000032036538",
         "Arrêté du 10 février 2016 (Division 245 — eaux intérieures)",
         "Division 245, art. ", "securite", kind="jorf"),
]
_BY_SOURCE = {t.source_id: t for t in TEXTS}

# Theme tagger: keyword → FR theme id, matched against the section breadcrumb +
# article heading. Order matters (first hit wins); falls back to the text default.
_THEME_RULES: list[tuple[str, str]] = [
    (r"écluse|barrage|ouvrage", "ecluses"),
    (r"signal|balis|pancarte|panneau|feux|fanal|marque", "signalisation_fluviale"),
    (r"rencontre|croisement|dépassement|trémat|priorit|règles de route|"
     r"barre et de route|vitesse|abordage|route", "regles_route"),
    (r"stationnement|amarrage|ancrage|mouillage|circulation", "voies_navigables"),
    (r"matériel|armement|sécurité|équipement|flottabilité|incendie|sauvetage|"
     r"assèchement", "securite"),
    (r"titre de navigation|permis|certificat|déclaration|sanction|alcool|"
     r"pénal|amende|immatricul|enregistrement|radio", "reglementation"),
    (r"environnement|pollution|rejet|déchet|hydrocarbure|eaux usées|marpol",
     "environnement"),
]


def _theme(breadcrumb: str, heading: str, default: str) -> str:
    hay = f"{breadcrumb} {heading}".lower()
    for pat, theme in _THEME_RULES:
        if re.search(pat, hay):
            return theme
    return default


def _norm(s: str) -> str:
    return re.sub(r"[ \t]*\n[ \t\n]*", "\n", re.sub(r"[ \t]+", " ",
                  (s or "").replace("\xa0", " "))).strip()


def _content_text(root) -> str:
    return _norm("\n".join("".join(c.itertext())
                           for c in root.findall(".//BLOC_TEXTUEL/CONTENU")))


def _breadcrumb(root) -> list[str]:
    return [_norm("".join(t.itertext())) for t in root.iter("TITRE_TM")]


def parse_article(path: str, text: Text) -> KnowledgeUnit | None:
    """One in-force, in-scope article of `text` → KnowledgeUnit (else None)."""
    try:
        root = etree.parse(path).getroot()
    except etree.XMLSyntaxError:
        return None
    num = (root.findtext(".//META_ARTICLE/NUM") or "").strip()
    etat = (root.findtext(".//META_ARTICLE/ETAT") or "").strip()
    if etat != "VIGUEUR" or not num:
        return None
    if text.num and not re.match(text.num, num.replace(".", "")):
        return None
    body = _content_text(root)
    if not body:
        return None
    arti_id = (root.findtext(".//META_COMMUN/ID") or "").strip()
    crumbs = _breadcrumb(root)
    heading = body.split("\n", 1)[0][:120]
    ref = f"{text.ref_prefix}{num}"
    url = (JORF_URL if text.kind == "jorf" else ART_URL).format(id=arti_id)
    cross = [n for lien in root.iter("LIEN")
             if lien.get("sens") == "cible" and (n := (lien.get("num") or "").strip())]
    return KnowledgeUnit(
        id=make_id(text.source_id, ref),
        theme=_theme(" › ".join(crumbs), heading, text.default_theme),
        kind="article", ref=ref, title=(crumbs[-1] if crumbs else heading),
        text=body, source_id=text.source_id, source_name=text.name,
        source_url=url, retrieved=_dt.date.today().isoformat(),
        legal_version=(root.findtext(".//META_ARTICLE/DATE_DEBUT") or "").strip(),
        licence=_ETALAB.format(name=text.name), lang="fr", cross_refs=cross[:24])


def _article_root(key: str) -> str | None:
    hits = glob.glob(os.path.join(LEGI_DIR, "**", key, "article"), recursive=True)
    return hits[0] if hits else None


def extract() -> None:
    """Extract every TEXTS article + metadata subtree from the LEGI dump."""
    if not os.path.exists(DUMP):
        raise SystemExit(f"missing LEGI dump: {DUMP}\n"
                         "download Freemium_legi_global_*.tar.gz from "
                         "https://echanges.dila.gouv.fr/OPENDATA/LEGI/ first.")
    patterns = []
    for t in TEXTS:
        patterns += [f"*{t.key}/article/*.xml", f"*{t.key}/texte/*.xml"]
    subprocess.run(["tar", "xzf", DUMP, "--wildcards", "--no-anchored", *patterns],
                   cwd=LEGI_DIR, check=True)


def build_units() -> list[KnowledgeUnit]:
    units: list[KnowledgeUnit] = []
    missing = []
    for t in TEXTS:
        root = _article_root(t.key)
        if not root:
            missing.append(t.key)
            continue
        for f in glob.glob(os.path.join(root, "**", "LEGIARTI*.xml"), recursive=True):
            u = parse_article(f, t)
            if u:
                units.append(u)
    if missing:
        extract()
        if any(not _article_root(t.key) for t in TEXTS):
            raise SystemExit(f"extraction produced no article tree for: {missing}")
        return build_units()
    units.sort(key=lambda u: (u.source_id, u.ref))
    return units


def build_kb() -> dict:
    units = build_units()
    if not units:
        raise SystemExit("no units — did extraction run?")
    conn = connect(KB_DB)
    conn.executemany("DELETE FROM units WHERE source_id=?",
                     [(t.source_id,) for t in TEXTS])
    write_units(conn, units)
    set_meta(conn, kb_version=_dt.date.today().isoformat(), country="FR", source="legi")
    n = export_json(conn, KB_JSON)
    conn.close()
    by_src: dict[str, int] = {}
    for u in units:
        by_src[u.source_id] = by_src.get(u.source_id, 0) + 1
    return {"units": len(units), "exported": n, "by_source": by_src}


# --- verification: every seed citation must exist in the ingested law ----------
# Map a seed entry's `source` id to the ingested text it should resolve against.
_SEED_SRC_TO_KB = {"rgp": "code_transports", "code_transports": "code_transports",
                   "code_environnement": "code_environnement",
                   "decret_2007": "decret_2007", "arrete_2007": "arrete_2007",
                   "division_245": "division_245"}
_ART = re.compile(r"art\.?\s*([LRAD]?\.?\s?\d[\d-]*)", re.I)


def _artkey(token: str) -> str:
    return token.upper().replace(".", "").replace(" ", "").rstrip("-")


def verify_citations(units: list[KnowledgeUnit] | None = None) -> dict:
    """For every seed entry whose source is an ingested text, every article it
    names must exist in that text. Returns matched / missing / uncovered."""
    from .seed_fr import SEED
    units = units if units is not None else build_units()
    nums_by_src: dict[str, set] = {}
    for u in units:
        nums_by_src.setdefault(u.source_id, set()).add(
            _artkey(u.ref.split("art. ", 1)[1]))
    matched, missing, uncovered = 0, {}, {}
    for i, e in enumerate(SEED):
        kb_src = _SEED_SRC_TO_KB.get(e["source"])
        if not kb_src:
            uncovered.setdefault(e["source"], 0)
            uncovered[e["source"]] += 1
            continue
        toks = [_artkey(m.group(1)) for m in _ART.finditer(e["ref"])]
        for tok in toks:
            if tok in nums_by_src.get(kb_src, set()):
                matched += 1
            else:
                missing.setdefault(f"{kb_src}:{tok}", []).append(i)
    return {"by_source": {k: len(v) for k, v in nums_by_src.items()},
            "matched": matched, "missing": missing, "uncovered": uncovered}


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "extract":
        extract()
        print("extracted texts:", ", ".join(t.key for t in TEXTS))
    elif cmd == "verify":
        r = verify_citations()
        print("KB articles by source:", r["by_source"])
        print(f"matched citations: {r['matched']}")
        if r["missing"]:
            print(f"⚠ MISSING ({len(r['missing'])}):")
            for k, idxs in sorted(r["missing"].items()):
                print(f"   {k}  cited by seed #{idxs}")
        else:
            print("✓ every cited article of an ingested text exists in the law")
        print("not ingested (verified out-of-band):",
              {k: v for k, v in sorted(r["uncovered"].items())})
    else:
        s = build_kb()
        print(f"✓ France KB built: {KB_DB}  ({s['units']} articles)")
        print(f"  corpus exported: {KB_JSON}")
        print(f"  by source: {s['by_source']}")
