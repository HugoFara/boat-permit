"""Draft questions from the *multi-clause* annex figures the templated generator
can't touch — chiefly the night-lighting / day-signal configurations in ONI
Annexe 2 and RNL Annexe I (caption shaped like "vessel type; feu de mât: blanc;
feux de côté: vert/rouge …"). Those captions are a small spec, not a single
meaning, so they can't be a clean multiple-choice option; instead a subagent
authors a *text* question about the rule ("De nuit, quels feux un bateau à voile
naviguant au moteur doit-il porter ?"), grounded in the caption.

Same file-handoff pipeline as subagent_draft.py, language-aware (fr/de/it):

  emit <lang>          batch the semicolon figures by annex     -> figure_jobs[.lang].json
  (subagents)          author 0-or-1 question per figure        -> figure_answers[/lang]/<batch>.json
  ingest <lang>        ground (vs caption) + validate -> pending in the bank
  verify-emit <lang>   dump each pending draft + its caption     -> figure_verify[.lang].json
  (subagents)          adversarially verify, write               -> figure_verdicts[/lang]/<batch>.json
  verify-apply <lang>  approve the verified drafts (rest stay pending)

Questions are kind=rule_mc, theme=signalisation, *no image* (showing the diagram
would leak the answer). They carry the figure's public-domain provenance. The
durable inputs (figure_answers/, figure_verdicts/) are committed, so the bank
rebuilds via ingest + verify-apply — same contract as the prose drafts.
"""

from __future__ import annotations

import glob
import json
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.questions import prose                       # noqa: E402
from src.questions import schema as qschema           # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
# Figure questions are a Switzerland-only artifact (ONI/RNL Swiss-law diagrams);
# they read the CH KB/bank and live under the CH country namespace like any other.
KB_PATH = os.path.join(DATA, "kb.ch.sqlite")
QDB_PATH = os.path.join(DATA, "questions.ch.sqlite")
MIN_GROUNDING = 0.34
_PUBLIC_DOMAIN = ("oni", "rnl")


def _generator(lang: str) -> str:
    # Unprefixed by design: these generator strings are embedded in the committed
    # web bundles, so renaming them would break the bundles' byte-stability.
    return f"figure:{lang}.v1"


def _paths(lang: str) -> dict:
    # Under countries/ch/ like every country's inputs: base lang (fr) directly
    # there, de/it under a <lang>/ subdir.
    sub = os.path.join("countries", "ch") if lang == "fr" \
        else os.path.join("countries", "ch", lang)
    sfx = ".ch" if lang == "fr" else f".ch.{lang}"
    return {
        "jobs": os.path.join(DATA, f"figure_jobs{sfx}.json"),
        "answers": os.path.join(DATA, "figure_answers", sub),
        "verify_jobs": os.path.join(DATA, f"figure_verify{sfx}.json"),
        "verdicts_dir": os.path.join(DATA, "figure_verdicts", sub),
        "verdicts": os.path.join(DATA, f"figure_verdicts{sfx}.json"),
    }


def _batch_key(ref: str) -> str:
    """Group figures by source + annex so each subagent gets one coherent family
    (e.g. all ONI Annexe 2 lighting diagrams)."""
    m = re.match(r"\s*(ONI|RNL)\s+(Annexe?\s*[\w]+|Anhang\s*[\w]+|Allegato\s*[\w]+)", ref)
    if m:
        return f"{m.group(1)}_{m.group(2)}".replace(" ", "").lower()
    return "autre"


def _is_substantive(caption: str) -> bool:
    """Skip captions that can't anchor a question: too short (a colour gloss like
    'bande rouge; chiffres blancs') or a truncated cross-reference ('… Feux
    conformément à l’')."""
    c = caption.strip()
    if len(c) < 40:
        return False
    if re.search(r"conform[ée]ment\s+à\s+l[’']?\s*$", c, re.I):
        return False
    return True


def _load_figures(kb: sqlite3.Connection, lang: str) -> list[dict]:
    kb.row_factory = sqlite3.Row
    rows = kb.execute(
        """SELECT u.id, u.ref, u.theme, u.lang, u.source_id, u.source_name,
                  u.source_url, u.legal_version, u.licence, a.caption
           FROM units u JOIN assets a ON a.unit_id = u.id
           WHERE u.kind = 'annex_figure' AND u.lang = ? AND u.source_id IN (?,?)
           ORDER BY u.ref""", (lang, *_PUBLIC_DOMAIN)).fetchall()
    figs = []
    for r in rows:
        cap = (r["caption"] or "").strip()
        if ";" not in cap or not _is_substantive(cap):
            continue
        figs.append(dict(
            id=r["id"], ref=r["ref"], theme=r["theme"] or "signalisation",
            lang=r["lang"], source_name=r["source_name"], source_url=r["source_url"],
            legal_version=r["legal_version"], licence=r["licence"],
            text=cap, caption=cap))
    return figs


def cmd_emit(lang: str):
    kb = sqlite3.connect(KB_PATH)
    p = _paths(lang)
    figs = _load_figures(kb, lang)
    jobs: dict[str, list] = {}
    for f in figs:
        jobs.setdefault(_batch_key(f["ref"]), []).append(f)
    with open(p["jobs"], "w", encoding="utf-8") as fh:
        json.dump(jobs, fh, ensure_ascii=False, indent=2)
    os.makedirs(p["answers"], exist_ok=True)
    for b, items in sorted(jobs.items()):
        print(f"  {b:22} {len(items)} figures")
    print(f"→ {p['jobs']}  ({len(figs)} figures in {len(jobs)} batches; "
          f"answers dir: {p['answers']})")


def cmd_ingest(lang: str):
    p = _paths(lang)
    jobs = json.load(open(p["jobs"], encoding="utf-8"))
    conn = qschema.connect(QDB_PATH)
    grand = {"drafted": 0, "kept": 0, "invalid": 0, "weak_grounding": 0,
             "has_image": 0, "no_unit": 0}
    for batch, units in jobs.items():
        by_ref = {u["ref"]: u for u in units}
        path = os.path.join(p["answers"], f"{batch}.json")
        if not os.path.exists(path):
            print(f"  {batch:22} (no answers file — skipped)")
            continue
        data = json.load(open(path, encoding="utf-8"))
        drafts = data["drafts"] if isinstance(data, dict) else data
        kept_q, st = [], {"drafted": 0, "kept": 0, "invalid": 0, "weak_grounding": 0}
        for d in drafts:
            unit = by_ref.get(d.get("ref"))
            if unit is None:
                grand["no_unit"] += 1
                continue
            if not d.get("questions"):                 # subagent declined this figure
                continue
            unit["_generator"] = _generator(lang)
            qs = prose.parse_drafts(json.dumps({"questions": d["questions"]}), unit)
            for q in qs:
                st["drafted"] += 1
                if any(c.image for c in q.choices) or q.image:   # text-only by design
                    grand["has_image"] += 1
                    continue
                if qschema.validate(q):
                    st["invalid"] += 1
                    continue
                correct = " ".join(c.text for c in q.choices if c.is_correct)
                if prose.grounding_score(correct, unit["text"]) < MIN_GROUNDING:
                    st["weak_grounding"] += 1
                    continue
                kept_q.append(q)
                st["kept"] += 1
        qschema.write_questions(conn, kept_q)
        for k in ("drafted", "kept", "invalid", "weak_grounding"):
            grand[k] += st[k]
        print(f"  {batch:22} drafted {st['drafted']:3}  kept {st['kept']:3}  "
              f"invalid {st['invalid']}  weak {st['weak_grounding']}")
    print(f"→ pending written. totals: {grand}")
    print("  review queue:", qschema.counts_by_status(conn))


def cmd_verify_emit(lang: str):
    p = _paths(lang)
    conn = qschema.connect(QDB_PATH)
    conn.row_factory = sqlite3.Row
    kb = sqlite3.connect(KB_PATH)
    kb.row_factory = sqlite3.Row
    out = []
    rows = conn.execute(
        "SELECT * FROM questions WHERE review_status='pending' AND generator=? "
        "ORDER BY prov_ref, id", (_generator(lang),)).fetchall()
    for r in rows:
        cap = kb.execute(
            "SELECT a.caption FROM assets a WHERE a.unit_id=?",
            (r["prov_unit_id"],)).fetchone()
        choices = [{"text": c["text"], "correct": bool(c["is_correct"])}
                   for c in conn.execute(
                       "SELECT text, is_correct FROM choices WHERE question_id=? "
                       "ORDER BY idx", (r["id"],))]
        out.append({"qid": r["id"], "batch": _batch_key(r["prov_ref"]),
                    "ref": r["prov_ref"], "stem": r["stem"],
                    "polarity": r["polarity"], "choices": choices,
                    "caption": cap["caption"] if cap else ""})
    os.makedirs(p["verdicts_dir"], exist_ok=True)
    with open(p["verify_jobs"], "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
    print(f"→ {p['verify_jobs']} ({len(out)} drafts to verify; "
          f"verdicts dir: {p['verdicts_dir']})")


def cmd_verify_apply(lang: str):
    p = _paths(lang)
    merged = {}
    for f in glob.glob(os.path.join(p["verdicts_dir"], "*.json")):
        merged.update(json.load(open(f, encoding="utf-8")))
    with open(p["verdicts"], "w", encoding="utf-8") as fh:
        json.dump(merged, fh, ensure_ascii=False, indent=2)
    conn = qschema.connect(QDB_PATH)
    passed = [q for q, v in merged.items() if str(v).lower().startswith("pass")]
    n = qschema.set_review_status(conn, passed, "approved")
    print(f"  approved {n} verified figure drafts ({len(merged) - len(passed)} left pending)")
    print("  review queue:", qschema.counts_by_status(conn))


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    lang = sys.argv[2] if len(sys.argv) > 2 else "fr"
    fns = {"emit": cmd_emit, "ingest": cmd_ingest,
           "verify-emit": cmd_verify_emit, "verify-apply": cmd_verify_apply}
    if cmd not in fns:
        sys.exit(f"usage: python tools/subagent_figures.py {{{'|'.join(fns)}}} [lang]")
    fns[cmd](lang)


if __name__ == "__main__":
    main()
