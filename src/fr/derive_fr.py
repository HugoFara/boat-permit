"""Derive candidate questions from the ingested French law (`legi_kb.json`).

The corpus is the actual statute (the RGP, the permis decree, Division 245), so a
question drafted *from an article's text* is **grounded in the source, not recall**
— the standing rule. Each draft is tied to its article (number + Légifrance URL),
carries our canonical citation, and lands as `status="pending"` in the committed
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
    """{(kb_source, NUM) → unit} for the ingested corpus."""
    out = {}
    for u in json.load(open(KB_JSON, encoding="utf-8"))["units"]:
        num = u["ref"].split("art. ", 1)[1]
        out[(u["source_id"], num)] = u
    return out


def select() -> list[dict]:
    """Resolve TARGETS against the corpus → job payloads (with article text)."""
    idx = _kb_index()
    jobs = []
    for num, src, theme in TARGETS:
        u = idx.get((_SEED_SRC_TO_KB[src], num))
        if not u:
            raise SystemExit(f"target absent from KB: {src} art. {num}")
        jobs.append({
            "option": "eaux_interieures", "theme": theme, "source": src,
            "article_num": num, "ref": f"{_REF_PREFIX[src]}{num}",
            "url": u["source_url"], "kb_heading": u["text"].split("\n", 1)[0][:90],
            "text": u["text"]})
    return jobs


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
    idx = _kb_index()
    targets = {f"{_REF_PREFIX[s]}{n}": (n, s, t) for n, s, t in TARGETS}
    prior = {d["ref"]: d for d in load_drafts()}
    raw: list[dict] = []
    for f in sorted(glob.glob(draft_glob or os.path.join(JOBS_DIR, "draft_*.json"))):
        raw += json.load(open(f, encoding="utf-8"))
    out, problems = [], []
    for d in raw:
        ref = d.get("ref", "")
        if ref not in targets:
            problems.append(f"draft ref not a target: {ref!r}")
            continue
        num, src, theme = targets[ref]
        entry = {
            "option": "eaux_interieures", "theme": theme, "source": src, "ref": ref,
            "polarity": d.get("polarity", "affirmative"),
            "fr": d["fr"], "en": d["en"], "choices": d["choices"],
            "status": prior.get(ref, {}).get("status", "pending"),
            "generator": GENERATOR,
            "article": {"num": num, "source_id": _SEED_SRC_TO_KB[src],
                        "url": idx[(_SEED_SRC_TO_KB[src], num)]["source_url"]}}
        errs = _validate(entry)
        if errs:
            problems.append(f"{ref}: {'; '.join(errs)}")
            continue
        out.append(entry)
    out.sort(key=lambda e: (e["theme"], e["ref"]))
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
