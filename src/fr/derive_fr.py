"""Derive candidate questions from the ingested corpora.

Two grounded corpora feed this: the French **law** (`legi_kb.json` — the RGP, the
permis decree, Division 245) for **eaux intérieures**, and the **reference facts**
(`reference_kb.json` — IALA buoyage + SHOM tides) for **côtière**. A question
drafted *from a unit's text* is **grounded in the source, not recall** — the
standing rule. Each draft is tied to its unit (article number + Légifrance URL, or
the reference unit + its IALA/SHOM URL), carries our canonical citation, and lands
as `status="pending"` in the committed
`src/fr/derived_drafts.json`: it is **not served** until reviewed/approved (the
exam schema only exports `approved`/`auto_approved`). `build_fr` merges the
approved ones into the bank; promoting is a deliberate review act.

Flow:
    python -m src.fr.derive_fr jobs      # select target articles → data/fr_derive/jobs.json
    # (drafting agents read jobs.json and write data/fr_derive/draft_*.json)
    python -m src.fr.derive_fr ingest    # validate drafts → src/fr/derived_drafts.json (pending)
    python -m src.fr.derive_fr review    # list pending / approve by ref
    python -m src.fr.derive_fr report    # human-readable Markdown of the drafts

The citation + source + theme of each draft come from `TARGETS` (curated against
the corpus, so provenance is authoritative); a drafting agent only supplies the
question *content* (stem / explanation / choices), strictly from the article text.
"""

from __future__ import annotations

import glob
import json
import os

from . import sources_fr, exam_fr, themes_fr  # noqa: F401
from .seed_fr import SEED  # noqa: F401  (kept for parity / future dedup)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
KB_JSON = os.path.join(ROOT, "src", "fr", "legi_kb.json")
REF_JSON = os.path.join(ROOT, "src", "fr", "reference_kb.json")
DRAFTS_JSON = os.path.join(ROOT, "src", "fr", "derived_drafts.json")   # committed
JOBS_DIR = os.path.join(ROOT, "data", "fr_derive")                     # git-ignored
JOBS_JSON = os.path.join(JOBS_DIR, "jobs.json")
GENERATOR = "derive:legi.v1"

# Curated target articles (read off the ingested corpus). Each is a clearly
# testable rule NOT already covered by a hand-authored seed. (num, source, theme).
# All eaux_interieures — the ingested law is the inland RGP / permit / Division 245.
TARGETS: list[tuple[str, str, str]] = [
    # --- Règles de route (fluvial) -------------------------------------------
    ("A4241-53-2", "rgp", "regles_route"),    # bateaux rapides laissent la route
    ("A4241-53-10", "rgp", "regles_route"),   # dépassement — dispositions générales
    ("A4241-53-37", "rgp", "regles_route"),   # priorités spéciales (rencontre/croisement)
    ("A4241-53-25", "rgp", "regles_route"),   # bacs — principes généraux
    ("A4241-53-19", "rgp", "regles_route"),   # interdiction de traîner ancres/câbles
    # --- Écluses, ponts, barrages --------------------------------------------
    ("A4241-53-26", "rgp", "ecluses"),        # passage des ponts et barrages
    ("A4241-53-32", "rgp", "ecluses"),        # priorité de passage aux écluses
    ("A4241-54-9", "rgp", "ecluses"),         # stationnement dans les garages d'écluses
    # --- Signalisation des voies et des bateaux ------------------------------
    ("A4241-48-2", "rgp", "signalisation_fluviale"),   # feux et fanaux (règles générales)
    ("A4241-48-4", "rgp", "signalisation_fluviale"),   # cylindres/ballons/cônes (marques de jour)
    ("A4241-48-5", "rgp", "signalisation_fluviale"),   # feux et signaux interdits
    ("A4241-48-16", "rgp", "signalisation_fluviale"),  # signalisation des bacs faisant route
    ("A4241-48-30", "rgp", "signalisation_fluviale"),  # signaux de détresse (visuels)
    ("A4241-49-2", "rgp", "signalisation_fluviale"),   # usage des signaux sonores
    ("A4241-49-3", "rgp", "signalisation_fluviale"),   # signaux sonores interdits
    ("A4241-51-1", "rgp", "signalisation_fluviale"),   # signalisation (annexe 7)
    ("A4241-51-2", "rgp", "signalisation_fluviale"),   # balisage (annexe 8)
    # --- Voies navigables & stationnement ------------------------------------
    ("A4241-54-3", "rgp", "voies_navigables"),  # ancrage interdit (où)
    ("A4241-54-4", "rgp", "voies_navigables"),  # amarrage interdit (où)
    ("A4241-54-5", "rgp", "voies_navigables"),  # aires de stationnement (signalées)
    ("A4241-54-8", "rgp", "voies_navigables"),  # garde et surveillance
    ("A4241-54-10", "rgp", "voies_navigables"), # raccordement au réseau électrique
    # --- Sécurité (Division 245) ---------------------------------------------
    ("1", "division_245", "securite"),    # champ d'application (longueur, eaux intérieures)
    ("5", "division_245", "securite"),    # armement « eaux intérieures abritées »
    ("11", "division_245", "securite"),   # engins à sustentation hydropropulsés
    # --- Réglementation (décret permis) --------------------------------------
    ("1", "decret_2007", "reglementation"),   # définition « bateau de plaisance »
    ("10", "decret_2007", "reglementation"),  # initiation à la conduite des VNM
    ("11", "decret_2007", "reglementation"),  # voies et plans d'eau intérieurs

    # ===================== BATCH 2 (RGP arrêté + décret) =====================
    # --- Règles de route -----------------------------------------------------
    ("A4241-53-4", "rgp", "regles_route"),    # passage/dépassement — principes généraux
    ("A4241-53-18", "rgp", "regles_route"),   # navigation à la même hauteur / s'approcher
    ("A4241-53-20", "rgp", "regles_route"),   # navigation à la dérive et arrêt
    ("A4241-53-13", "rgp", "regles_route"),   # secteurs où la route est prescrite
    ("R4241-10", "rgp", "regles_route"),      # vitesse adaptée aux circonstances
    ("R4241-6", "rgp", "regles_route"),       # le conducteur doit être à bord en route
    ("R4241-4", "rgp", "regles_route"),       # équipage/passagers se conforment aux ordres
    # --- Sécurité / devoirs du conducteur ------------------------------------
    ("R4241-15", "rgp", "securite"),          # mesures de précaution (prudence)
    ("R4241-16", "rgp", "securite"),          # personnes à bord obéissent au conducteur
    ("R4241-18", "rgp", "securite"),          # sinistre/incendie à bord
    ("R4241-19", "rgp", "securite"),          # objets débordant sur les côtés
    ("R4241-22", "rgp", "securite"),          # perte d'objet / obstacle rencontré
    ("R4241-24", "rgp", "securite"),          # bateau échoué ou coulé
    ("R4241-25", "rgp", "securite"),          # renforcer les amarres (crue/danger)
    # --- Voies navigables & contrôle -----------------------------------------
    ("A4241-54-6", "rgp", "voies_navigables"),  # aires de stationnement particulières
    ("R4241-27", "rgp", "voies_navigables"),    # chargement et zone de non-visibilité
    ("R4241-41", "rgp", "voies_navigables"),    # présenter les documents aux agents
    ("R4241-40", "rgp", "voies_navigables"),    # donner aux agents les moyens de contrôle
    ("R4241-39", "rgp", "voies_navigables"),    # se conformer aux ordres des agents
    # --- Écluses, ponts, ouvrages --------------------------------------------
    ("A4241-53-27", "rgp", "ecluses"),        # passage des ponts fixes
    ("R4241-71", "rgp", "ecluses"),           # passerelles d'écluse — interdictions
    ("R4241-21", "rgp", "ecluses"),           # dommages aux ouvrages d'art
    # --- Signalisation des bateaux -------------------------------------------
    ("A4241-48-3", "rgp", "signalisation_fluviale"),   # pavillons, panneaux et flammes
    ("A4241-48-7", "rgp", "signalisation_fluviale"),   # interdiction lumières éblouissantes
    ("A4241-48-6", "rgp", "signalisation_fluviale"),   # feux de secours
    ("A4241-49-4", "rgp", "signalisation_fluviale"),   # signaux de détresse sonores
    ("R4241-49", "rgp", "signalisation_fluviale"),     # dispositif d'émission de signaux sonores
    ("R4241-50", "rgp", "signalisation_fluviale"),     # radar par visibilité réduite
    ("R4241-48", "rgp", "signalisation_fluviale"),     # signalisation visuelle des bateaux
    # --- Environnement -------------------------------------------------------
    ("R4241-23", "rgp", "environnement"),     # jeter/laisser tomber dans les eaux
    ("R4241-65", "rgp", "environnement"),     # carnet de contrôle des huiles usées
]

# Côtière targets: reference units (IALA buoyage / SHOM tides) — identified by the
# unit's `ref`; option=cotiere, theme+source taken from the unit. The corpus is the
# verified-facts KB (src/fr/reference_kb.json), built by src/fr/reference_fr.py.
COTIERE_TARGETS: list[str] = [
    "IALA R1001 §2.1.3 — marque latérale bâbord (région A)",
    "IALA R1001 §2.1.3 — marque latérale tribord (région A)",
    "IALA R1001 §2.1.5 — marques de chenal préféré (région A)",
    "IALA R1001 §2.2.4 — marque cardinale Nord",
    "IALA R1001 §2.2.4 — marque cardinale Est",
    "IALA R1001 §2.2.4 — marque cardinale Sud",
    "IALA R1001 §2.2.4 — marque cardinale Ouest",
    "IALA R1001 §2.3 — marque de danger isolé",
    "IALA R1001 §2.4 — marque d'eaux saines",
    "IALA R1001 §2.5 — marque spéciale",
    "SHOM — zéro hydrographique (ZH)",
    "SHOM — marnage",
    "SHOM — coefficient de marée",
    "SHOM — vives-eaux et mortes-eaux",
    "SHOM — flot et jusant",
    "SHOM — marée semi-diurne et cycle",
    "SHOM — niveaux caractéristiques de la marée",
    "Règle des douzièmes (méthode de l'annuaire des marées)",
    "SHOM — étale",
]

# The source a seed/draft `source` id resolves to in the ingested KB.
_SEED_SRC_TO_KB = {"rgp": "code_transports", "code_transports": "code_transports",
                   "code_environnement": "code_environnement",
                   "decret_2007": "decret_2007", "arrete_2007": "arrete_2007",
                   "division_245": "division_245"}
# Human ref prefix per seed source (matches seed_fr's citation style).
_REF_PREFIX = {"rgp": "RGP, art. ", "division_245": "Division 245, art. ",
               "decret_2007": "Décret 2007-1167, art. ",
               "code_environnement": "Code de l'environnement, art. ",
               "code_transports": "Code des transports, art. "}


def _kb_index() -> dict[tuple[str, str], dict]:
    """{(kb_source, NUM) → unit} for the ingested LEGI law corpus."""
    out = {}
    for u in json.load(open(KB_JSON, encoding="utf-8"))["units"]:
        num = u["ref"].split("art. ", 1)[1]
        out[(u["source_id"], num)] = u
    return out


def _ref_index() -> dict[str, dict]:
    """{ref → unit} for the IALA/SHOM reference-facts corpus."""
    if not os.path.exists(REF_JSON):
        return {}
    return {u["ref"]: u for u in json.load(open(REF_JSON, encoding="utf-8"))["units"]}


def _targets() -> dict[str, dict]:
    """Every derivation target, keyed by its citation `ref`:
      - LEGI article targets (eaux intérieures) from TARGETS, resolved in legi_kb;
      - reference-fact targets (côtière) from COTIERE_TARGETS, resolved in reference_kb.
    Each value carries the option/theme/source, the source text + heading (for the
    drafting job), and the `article` provenance link."""
    legi, ref_idx = _kb_index(), _ref_index()
    out: dict[str, dict] = {}
    for num, src, theme in TARGETS:
        u = legi.get((_SEED_SRC_TO_KB[src], num))
        if not u:
            raise SystemExit(f"LEGI target absent: {src} art. {num}")
        ref = f"{_REF_PREFIX[src]}{num}"
        out[ref] = {"option": "eaux_interieures", "theme": theme, "source": src,
                    "generator": "derive:legi.v1",
                    "text": u["text"], "heading": u["text"].split("\n", 1)[0][:90],
                    "article": {"num": num, "source_id": _SEED_SRC_TO_KB[src],
                                "url": u["source_url"]}}
    for ref in COTIERE_TARGETS:
        u = ref_idx.get(ref)
        if not u:
            raise SystemExit(f"côtière target absent from reference_kb: {ref!r}")
        out[ref] = {"option": "cotiere", "theme": u["theme"], "source": u["source_id"],
                    "generator": "derive:ref.v1",
                    "text": u["text"], "heading": u["title"],
                    "article": {"unit_ref": ref, "source_id": u["source_id"],
                                "url": u["source_url"]}}
    return out


def select() -> list[dict]:
    """Resolve all targets against the corpora → job payloads (with source text)."""
    return [{"option": t["option"], "theme": t["theme"], "source": t["source"],
             "ref": ref, "url": t["article"]["url"], "kb_heading": t["heading"],
             "text": t["text"]}
            for ref, t in _targets().items()]


def write_jobs() -> str:
    os.makedirs(JOBS_DIR, exist_ok=True)
    jobs = select()
    with open(JOBS_JSON, "w", encoding="utf-8") as fh:
        json.dump(jobs, fh, ensure_ascii=False, indent=2)
    return JOBS_JSON


# --- ingest agent drafts -------------------------------------------------------
def _validate(entry: dict) -> list[str]:
    errs = []
    if entry["option"] not in exam_fr.PROFILES:
        errs.append("bad option")
    if not themes_fr.is_valid(entry["theme"]):
        errs.append(f"bad theme {entry['theme']!r}")
    if entry["source"] not in sources_fr.FR_SOURCES:
        errs.append(f"unknown source {entry['source']!r}")
    for lg in ("fr", "en"):
        if not entry.get(lg, {}).get("stem", "").strip():
            errs.append(f"empty {lg} stem")
    ch = entry.get("choices", [])
    if len(ch) != 3:
        errs.append("must have 3 choices")
    if sum(1 for c in ch if c.get("correct")) != 1:
        errs.append("exactly one correct choice required")
    for c in ch:
        if not (c.get("fr", "").strip() and c.get("en", "").strip()):
            errs.append("empty choice text")
    return errs


def ingest(draft_glob: str | None = None) -> dict:
    """Merge agent draft files (`data/fr_derive/draft_*.json`) into the committed
    `derived_drafts.json`, keyed by ref. Every draft must name a target article
    and be well-formed. Existing approvals/rejections are preserved by ref."""
    targets = _targets()
    # Start from the existing committed drafts (durable record) and overlay any
    # new/updated drafts from the scratch files — so earlier batches survive even
    # if their scratch draft files are gone, and approvals/rejections are kept.
    merged = {d["ref"]: d for d in load_drafts()}
    raw: list[dict] = []
    for f in sorted(glob.glob(draft_glob or os.path.join(JOBS_DIR, "draft_*.json"))):
        raw += json.load(open(f, encoding="utf-8"))
    problems = []
    for d in raw:
        ref = d.get("ref", "")
        t = targets.get(ref)
        if not t:
            problems.append(f"draft ref not a target: {ref!r}")
            continue
        entry = {
            "option": t["option"], "theme": t["theme"], "source": t["source"],
            "ref": ref, "polarity": d.get("polarity", "affirmative"),
            "fr": d["fr"], "en": d["en"], "choices": d["choices"],
            "status": merged.get(ref, {}).get("status", "pending"),
            "generator": t.get("generator", GENERATOR), "article": t["article"]}
        errs = _validate(entry)
        if errs:
            problems.append(f"{ref}: {'; '.join(errs)}")
            continue
        merged[ref] = entry
    out = sorted(merged.values(), key=lambda e: (e["option"], e["theme"], e["ref"]))
    with open(DRAFTS_JSON, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
    return {"ingested": len(out), "problems": problems,
            "by_status": _counts(out)}


def load_drafts() -> list[dict]:
    if not os.path.exists(DRAFTS_JSON):
        return []
    return json.load(open(DRAFTS_JSON, encoding="utf-8"))


def approved_entries() -> list[dict]:
    """Approved drafts in seed shape (for build_fr to serve)."""
    return [{k: d[k] for k in ("option", "theme", "source", "ref", "polarity",
                               "fr", "en", "choices")}
            for d in load_drafts() if d.get("status") == "approved"]


def set_status(refs: list[str], status: str) -> int:
    drafts = load_drafts()
    n = 0
    for d in drafts:
        if d["ref"] in refs:
            d["status"] = status
            n += 1
    with open(DRAFTS_JSON, "w", encoding="utf-8") as fh:
        json.dump(drafts, fh, ensure_ascii=False, indent=2)
    return n


def _counts(drafts) -> dict:
    out: dict[str, int] = {}
    for d in drafts:
        out[d["status"]] = out.get(d["status"], 0) + 1
    return out


def report() -> str:
    lines = ["# France — questions dérivées du droit ingéré (à valider)\n"]
    for d in load_drafts():
        ok = next(c for c in d["choices"] if c["correct"])
        lines.append(f"## [{d['status']}] {d['ref']}  ({d['theme']})")
        lines.append(f"<{d['article']['url']}>\n")
        lines.append(f"**{d['fr']['stem']}**")
        for c in d["choices"]:
            lines.append(f"- {'✅' if c['correct'] else '◻️'} {c['fr']}")
        lines.append(f"\n*{d['fr']['explanation']}*\n")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    if cmd == "jobs":
        print("wrote", write_jobs(), f"({len(select())} target articles)")
    elif cmd == "ingest":
        r = ingest()
        print(f"ingested {r['ingested']} drafts → {DRAFTS_JSON}  {r['by_status']}")
        for p in r["problems"]:
            print("  ⚠", p)
    elif cmd == "review":
        for d in load_drafts():
            print(f"  [{d['status']:8}] {d['ref']}")
        print(f"\n{_counts(load_drafts())}  — approve: "
              f"python -m src.fr.derive_fr approve '<ref>' ['<ref>' …]")
    elif cmd == "approve":
        print("approved:", set_status(sys.argv[2:], "approved"))
    elif cmd == "reject":
        print("rejected:", set_status(sys.argv[2:], "rejected"))
    else:
        print(report())
