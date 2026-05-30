"""Ingest French inland-navigation law from the official DILA **LEGI** open data.

This is France's analogue of the Swiss Fedlex pipeline (`src/parsers/akn.py`): it
turns the consolidated **Code des transports** — *Quatrième partie : navigation
intérieure et transport fluvial* (the RGP, the titre-de-navigation regime, the
sanctions) — into article-level `KnowledgeUnit`s, so the France question bank can
be **grounded in and verified against the actual statute text** rather than recall.

Source: the LEGI dataset (73 consolidated codes), published by the DILA as
structured XML under the **Licence Ouverte / Etalab** — freely reusable. We read
the bulk `Freemium_legi_global_*.tar.gz` dump (not the API, no credentials). Each
in-force article is one XML file under the text's own `article/` subtree; we filter
by `<NUM>` (Part 4 = the `[LRAD]4xxx` series) and keep only `ETAT=VIGUEUR`.

The durable artifact is the committed KB JSON export (`data/kb.fr.json` is git-
ignored like the Swiss KB, so we export a committed copy under `src/fr/`); the
1.2 GB dump itself stays out of git (`data/raw/`). Rebuild:

    python -m src.fr.legi extract   # dump -> data/raw/legi/ (needs the tar)
    python -m src.fr.legi build     # extracted articles -> KB + corpus JSON
    python -m src.fr.legi verify     # cross-check seed_fr citations vs the KB
"""

from __future__ import annotations

import datetime as _dt
import glob
import os
import re
import subprocess

from lxml import etree

from ..schema import KnowledgeUnit, make_id, connect, write_units, set_meta, export_json
from . import themes_fr  # noqa: F401  — registers FR themes with the shared validator

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
LEGI_DIR = os.path.join(ROOT, "data", "raw", "legi")
DUMP = os.path.join(LEGI_DIR, "legi_global.tar.gz")
KB_DB = os.path.join(ROOT, "data", "kb.fr.sqlite")
KB_JSON = os.path.join(ROOT, "src", "fr", "legi_kb.json")   # committed corpus

# The Code des transports. Its articles carry NUM like "L4221-1", "R4241-62",
# "A4241-53-6": letter (L=loi / R=décret / A=arrêté / D=décret-CE) + the part-4
# numbering. We keep the whole 4ᵉ partie (navigation intérieure & transport
# fluvial) — that is the RGP plus the titre/sanctions regime our bank cites.
CDT_CID = "LEGITEXT000023086525"
_PART4 = re.compile(r"^[LRAD]4\d{3}")            # 4000–4999 → navigation intérieure
LICENCE = ("Licence Ouverte / Open Licence 2.0 (Etalab) — Code des transports "
           "(DILA, base LEGI), librement réutilisable.")
SOURCE_NAME = "Code des transports (Légifrance / DILA, base LEGI)"
ART_URL = "https://www.legifrance.gouv.fr/codes/article_lc/{id}"

# Theme tagger: keyword → FR theme id (themes_fr.FR_THEMES), matched against the
# section breadcrumb + article heading. Order matters (first hit wins).
_THEME_RULES: list[tuple[str, str]] = [
    (r"écluse|barrage|ouvrage", "ecluses"),
    (r"signal|balis|pancarte|marque|panneau", "signalisation_fluviale"),
    (r"feux|signalisation de nuit|fanal", "signalisation_fluviale"),
    (r"rencontre|croisement|dépassement|trémat|priorit|règles de route|"
     r"barre et de route|vitesse|abordage", "regles_route"),
    (r"stationnement|amarrage|ancrage|mouillage|circulation|navigation des", "voies_navigables"),
    (r"matériel|armement|sécurité|équipement|flottabilité|incendie|sauvetage", "securite"),
    (r"titre de navigation|permis|certificat|déclaration|sanction|alcool|"
     r"pénal|amende|immatricul|enregistrement|jaugeage", "reglementation"),
    (r"environnement|pollution|rejet|déchet|hydrocarbure|eaux usées", "environnement"),
]


def _theme(breadcrumb: str, heading: str) -> str:
    hay = f"{breadcrumb} {heading}".lower()
    for pat, theme in _THEME_RULES:
        if re.search(pat, hay):
            return theme
    return "voies_navigables"       # the generic inland-navigation bucket


def _norm(s: str) -> str:
    return re.sub(r"[ \t]*\n[ \t\n]*", "\n", re.sub(r"[ \t]+", " ",
                  (s or "").replace("\xa0", " "))).strip()


def _content_text(article) -> str:
    """Visible text of <BLOC_TEXTUEL><CONTENU>, paragraphs kept as lines."""
    blocs = article.findall(".//BLOC_TEXTUEL/CONTENU")
    parts = []
    for c in blocs:
        for p in c.iter():
            if p.tag in ("p", "br") and p.tail:
                pass
        parts.append("\n".join(seg for seg in ("".join(c.itertext()),) ))
    return _norm("\n".join(parts))


def _breadcrumb(article) -> list[str]:
    return [_norm("".join(t.itertext())) for t in article.iter("TITRE_TM")]


def parse_article(path: str) -> KnowledgeUnit | None:
    """One in-force Part-4 article → KnowledgeUnit (None if out of scope)."""
    try:
        root = etree.parse(path).getroot()
    except etree.XMLSyntaxError:
        return None
    num = (root.findtext(".//META_ARTICLE/NUM") or "").strip()
    etat = (root.findtext(".//META_ARTICLE/ETAT") or "").strip()
    if etat != "VIGUEUR" or not _PART4.match(num.replace(".", "")):
        return None
    arti_id = (root.findtext(".//META_COMMUN/ID") or "").strip()
    date_debut = (root.findtext(".//META_ARTICLE/DATE_DEBUT") or "").strip()
    text = _content_text(root)
    if not text:
        return None
    crumbs = _breadcrumb(root)
    section = crumbs[-1] if crumbs else ""
    heading = text.split("\n", 1)[0][:120]      # the article's own subject line
    ref = f"Code des transports, art. {num}"
    title = section or heading
    cross = []
    for lien in root.iter("LIEN"):
        n = (lien.get("num") or "").strip()
        if lien.get("sens") == "cible" and n:
            cross.append(n)
    return KnowledgeUnit(
        id=make_id("code_transports", ref),
        theme=_theme(" › ".join(crumbs), heading),
        kind="article", ref=ref, title=title, text=text,
        source_id="code_transports", source_name=SOURCE_NAME,
        source_url=ART_URL.format(id=arti_id) if arti_id else "",
        retrieved=_dt.date.today().isoformat(),
        legal_version=date_debut, licence=LICENCE, lang="fr",
        cross_refs=cross[:24])


def _cdt_article_root() -> str | None:
    hits = glob.glob(os.path.join(LEGI_DIR, "**", CDT_CID, "article"), recursive=True)
    return hits[0] if hits else None


def extract() -> str:
    """Extract the Code des transports article subtree from the LEGI dump."""
    if not os.path.exists(DUMP):
        raise SystemExit(f"missing LEGI dump: {DUMP}\n"
                         "download Freemium_legi_global_*.tar.gz from "
                         "https://echanges.dila.gouv.fr/OPENDATA/LEGI/ first.")
    subprocess.run(
        ["tar", "xzf", DUMP, "--wildcards", "--no-anchored",
         f"*{CDT_CID}/article/*.xml", f"*{CDT_CID}/texte/*.xml"],
        cwd=LEGI_DIR, check=True)
    root = _cdt_article_root()
    if not root:
        raise SystemExit("extraction produced no article tree")
    return root


def build_units() -> list[KnowledgeUnit]:
    root = _cdt_article_root()
    if not root:
        root = extract()
    units = []
    for f in glob.glob(os.path.join(root, "**", "LEGIARTI*.xml"), recursive=True):
        u = parse_article(f)
        if u:
            units.append(u)
    units.sort(key=lambda u: u.ref)
    return units


def build_kb() -> dict:
    units = build_units()
    if not units:
        raise SystemExit("no units — did extraction run?")
    version = _dt.date.today().isoformat()
    conn = connect(KB_DB)
    conn.execute("DELETE FROM units WHERE source_id='code_transports'")
    write_units(conn, units)
    set_meta(conn, kb_version=version, country="FR", source="legi")
    n = export_json(conn, KB_JSON)
    conn.close()
    by_theme: dict[str, int] = {}
    for u in units:
        by_theme[u.theme] = by_theme.get(u.theme, 0) + 1
    return {"units": len(units), "exported": n, "by_theme": by_theme,
            "version": version}


def verify_citations() -> dict:
    """Cross-check every seed_fr citation that names a Code-des-transports article
    against the ingested KB. Returns matched / missing article numbers."""
    from .seed_fr import SEED
    nums = {u.ref.split("art. ", 1)[1].replace(".", "").replace(" ", "")
            for u in build_units()}
    cited: dict[str, list[int]] = {}
    pat = re.compile(r"art\.?\s*([LRAD]\.?\s?4\d{3}[\d-]*)", re.I)
    for i, e in enumerate(SEED):
        for m in pat.finditer(e["ref"]):
            key = m.group(1).upper().replace(".", "").replace(" ", "")
            cited.setdefault(key, []).append(i)
    matched = {k: v for k, v in cited.items() if k in nums}
    missing = {k: v for k, v in cited.items() if k not in nums}
    return {"kb_articles": len(nums), "cited": len(cited),
            "matched": matched, "missing": missing}


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "extract":
        print("extracted to:", extract())
    elif cmd == "verify":
        r = verify_citations()
        print(f"KB articles: {r['kb_articles']} · cited Code-des-transports "
              f"articles: {r['cited']}")
        print(f"  matched ({len(r['matched'])}): {sorted(r['matched'])}")
        if r["missing"]:
            print(f"  ⚠ MISSING ({len(r['missing'])}):")
            for k, idxs in sorted(r["missing"].items()):
                print(f"     {k}  cited by seed #{idxs}")
        else:
            print("  ✓ every cited article exists in the ingested KB")
    else:
        s = build_kb()
        print(f"✓ France KB built: {KB_DB}  ({s['units']} articles, "
              f"version {s['version']})")
        print(f"  corpus exported: {KB_JSON}")
        print(f"  by theme: {s['by_theme']}")
