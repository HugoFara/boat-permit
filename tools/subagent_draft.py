"""Draft prose questions with *subagents* instead of the Anthropic API.

Same pipeline as `src/questions/prose.py` (select → prompt → parse → grounding →
validate → pending → review), but drafting and verification are done by Claude
subagents driven from the chat loop, with files as the hand-off. Country- and
language-aware. Stages (args: ``<cmd> [lang] [country]``, default ``fr CH``):

  emit <lang> <country>          select prose units per theme  -> draft_jobs[.code].json
  (subagents)                    draft per theme, write        -> draft_answers[/code]/<theme>.json
  ingest <lang> <country>        parse+ground+validate, write pending questions to the bank
  verify-emit <lang> <country>   dump each pending draft + its source -> verify_jobs[.code].json
  (subagents)                    adversarially verify, write   -> verdicts[/code]/<theme>.json
  verify-apply <lang> <country>  approve the verified drafts (rest stay pending)

Switzerland (the default) keeps the original flat, committed artifacts and the
unchanged Swiss theme plan / question bank; every other country is namespaced by
its code (draft_jobs.int.json, draft_answers/int/…, questions.int.sqlite) and
validated against its own taxonomy. Everything is grounded in public-domain /
freely-licensed source text; the verification pass is an independent check (a
different agent, told to default FAIL).
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import countries                              # noqa: E402
from src.questions import prose                        # noqa: E402
from src.questions import schema as qschema            # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
KB_PATH = os.path.join(DATA, "kb.sqlite")
MIN_GROUNDING = 0.34

# Switzerland's curated prose plan — (max units, questions-per-unit) per theme.
# Other countries draft every theme in their taxonomy (select_units caps to what
# is actually available per language; thin themes simply yield fewer).
_CH_PLAN = {
    "definitions": (2, 3),
    "meteorologie": (4, 3),
    "matelotage": (3, 3),
    "eaux_frontalieres": (6, 2),
    "lois": (8, 2),
}


def _plan(country) -> dict:
    if country.code == countries.DEFAULT:
        return _CH_PLAN
    return {theme: (999, 2) for theme in country.themes}


def _qdb(country) -> str:
    """The country's question bank (CH keeps the back-compat flat filename)."""
    if country.code == countries.DEFAULT:
        return os.path.join(DATA, "questions.sqlite")
    return os.path.join(DATA, f"questions.{country.code.lower()}.sqlite")


def _generator(lang: str, country) -> str:
    if country.code == countries.DEFAULT:
        return f"subagent:{lang}.v1"                   # unchanged for CH (fr/de/it)
    return f"subagent:{country.code.lower()}.{lang}.v1"


def _paths(lang: str, country) -> dict:
    # CH artifacts stay flat + committed; other countries namespace by code so banks
    # never collide (e.g. INT 'en' must not clash with a future English country).
    flat = country.code == countries.DEFAULT
    sfx = "" if flat else f".{country.code.lower()}"
    sub = "" if flat else country.code.lower()
    return {
        "jobs": os.path.join(DATA, f"draft_jobs{sfx}.json"),
        "answers": os.path.join(DATA, "draft_answers", sub),
        "verify_jobs": os.path.join(DATA, f"verify_jobs{sfx}.json"),
        "verdicts_dir": os.path.join(DATA, "verdicts", sub),
        "verdicts": os.path.join(DATA, f"verdicts{sfx}.json"),
    }


def cmd_emit(lang: str, country):
    kb = sqlite3.connect(KB_PATH)
    p = _paths(lang, country)
    jobs = {}
    for theme, (n_units, per_unit) in _plan(country).items():
        units = prose.select_units(kb, theme, limit=n_units, lang=lang)
        for u in units:
            u["_per_unit"] = per_unit
        if units:
            jobs[theme] = units
            print(f"  {theme:20} {len(units)} units × {per_unit} q")
    with open(p["jobs"], "w", encoding="utf-8") as fh:
        json.dump(jobs, fh, ensure_ascii=False, indent=2)
    os.makedirs(p["answers"], exist_ok=True)
    print(f"→ {p['jobs']}  (answers dir: {p['answers']})")


def cmd_ingest(lang: str, country):
    p = _paths(lang, country)
    valid = country.themes.__contains__
    jobs = json.load(open(p["jobs"], encoding="utf-8"))
    conn = qschema.connect(_qdb(country))
    grand = {"drafted": 0, "kept": 0, "invalid": 0, "weak_grounding": 0, "no_answer": 0}
    for theme, units in jobs.items():
        by_ref = {u["ref"]: u for u in units}
        path = os.path.join(p["answers"], f"{theme}.json")
        if not os.path.exists(path):
            print(f"  {theme:20} (no answers file — skipped)")
            continue
        data = json.load(open(path, encoding="utf-8"))
        drafts = data["drafts"] if isinstance(data, dict) else data
        kept_q, st = [], {"drafted": 0, "kept": 0, "invalid": 0, "weak_grounding": 0}
        for d in drafts:
            unit = by_ref.get(d.get("ref"))
            if unit is None:
                grand["no_answer"] += 1
                continue
            unit["_generator"] = _generator(lang, country)
            qs = prose.parse_drafts(json.dumps({"questions": d["questions"]}), unit)
            for q in qs:
                st["drafted"] += 1
                # Countries whose prose feeds a block-structured exam stamp the
                # exam-block id by theme (DE: BSO prose -> Bodensee Sachgebiete).
                if country.prose_block_for is not None:
                    q.block = country.prose_block_for(q.theme)
                if qschema.validate(q, is_valid_theme=valid):
                    st["invalid"] += 1
                    continue
                correct = " ".join(c.text for c in q.choices if c.is_correct)
                if prose.grounding_score(correct, unit["text"], lang) < MIN_GROUNDING:
                    st["weak_grounding"] += 1
                    continue
                kept_q.append(q)
                st["kept"] += 1
        qschema.write_questions(conn, kept_q, is_valid_theme=valid)
        for k in ("drafted", "kept", "invalid", "weak_grounding"):
            grand[k] += st[k]
        print(f"  {theme:20} drafted {st['drafted']:3}  kept {st['kept']:3}  "
              f"invalid {st['invalid']}  weak {st['weak_grounding']}")
    print(f"→ pending written to {_qdb(country)}. totals: {grand}")
    print("  review queue:", qschema.counts_by_status(conn))


def cmd_verify_emit(lang: str, country):
    p = _paths(lang, country)
    conn = qschema.connect(_qdb(country))
    conn.row_factory = sqlite3.Row
    kb = sqlite3.connect(KB_PATH)
    kb.row_factory = sqlite3.Row
    out = []
    rows = conn.execute(
        "SELECT * FROM questions WHERE review_status='pending' AND generator=? "
        "ORDER BY theme, id", (_generator(lang, country),)).fetchall()
    for r in rows:
        src = kb.execute("SELECT text FROM units WHERE id=?",
                         (r["prov_unit_id"],)).fetchone()
        choices = [{"text": c["text"], "correct": bool(c["is_correct"])}
                   for c in conn.execute(
                       "SELECT text, is_correct FROM choices WHERE question_id=? "
                       "ORDER BY idx", (r["id"],))]
        out.append({"qid": r["id"], "theme": r["theme"], "ref": r["prov_ref"],
                    "stem": r["stem"], "polarity": r["polarity"],
                    "choices": choices, "source_text": src["text"] if src else ""})
    os.makedirs(p["verdicts_dir"], exist_ok=True)
    with open(p["verify_jobs"], "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
    print(f"→ {p['verify_jobs']} ({len(out)} drafts to verify; "
          f"verdicts dir: {p['verdicts_dir']})")


def cmd_verify_apply(lang: str, country):
    import glob
    p = _paths(lang, country)
    merged = {}
    for f in glob.glob(os.path.join(p["verdicts_dir"], "*.json")):
        merged.update(json.load(open(f, encoding="utf-8")))
    with open(p["verdicts"], "w", encoding="utf-8") as fh:
        json.dump(merged, fh, ensure_ascii=False, indent=2)
    conn = qschema.connect(_qdb(country))
    passed = [q for q, v in merged.items() if str(v).lower().startswith("pass")]
    n = qschema.set_review_status(conn, passed, "approved")
    print(f"  approved {n} verified drafts ({len(merged) - len(passed)} left pending)")
    print("  review queue:", qschema.counts_by_status(conn))


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    lang = sys.argv[2] if len(sys.argv) > 2 else "fr"
    code = sys.argv[3] if len(sys.argv) > 3 else countries.DEFAULT
    fns = {"emit": cmd_emit, "ingest": cmd_ingest,
           "verify-emit": cmd_verify_emit, "verify-apply": cmd_verify_apply}
    if cmd not in fns:
        sys.exit(f"usage: python tools/subagent_draft.py "
                 f"{{{'|'.join(fns)}}} [lang] [country]")
    fns[cmd](lang, countries.get(code))


if __name__ == "__main__":
    main()
