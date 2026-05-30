"""Build the EN bank as an *unofficial translation* of the FR questions.

Swiss law has no official English text, so English questions can't be grounded —
they are translations of the (grounded, reviewed) French bank, clearly flagged
unofficial (export stamps meta.unofficial=true for non-grounded langs; the player
shows a banner). Subagents translate; files hand off. Stages:

  emit          dump exportable FR questions (text only)  -> translate_jobs.json
  (subagents)   translate per theme, write                -> translate_answers/<theme>.json
  ingest        rebuild EN questions from the FR ORIGINALS (structure, correct
                flags, images, provenance) with translated TEXT only -> pending
  verify-emit   pair each EN draft with its FR original    -> translate_verify.json
  (subagents)   check translation fidelity, write          -> translate_verdicts/<theme>.json
  verify-apply  approve faithful translations (rest stay pending)

Crucially, ingest never trusts the translation for structure: choice order and
is_correct come from the FR question, so a mistranslation can't flip the answer —
only the displayed text changes.
"""

from __future__ import annotations

import glob
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.questions import schema as qschema           # noqa: E402
from src.questions.schema import Question, Choice, Provenance, make_question_id  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
QDB_PATH = os.path.join(DATA, "questions.sqlite")
JOBS = os.path.join(DATA, "translate_jobs.json")
ANSWERS_DIR = os.path.join(DATA, "translate_answers")
VERIFY = os.path.join(DATA, "translate_verify.json")
VERDICTS_DIR = os.path.join(DATA, "translate_verdicts")

SRC_LANG = "fr"            # translate from the most complete, grounded bank
TGT_LANG = "en"
GENERATOR = "translation:en.v1"


def _fr_exportable(conn) -> list[Question]:
    return [q for q in qschema.load_questions(conn)
            if q.lang == SRC_LANG and q.review_status in qschema.EXPORTABLE_STATUSES]


def _answer_files() -> list[str]:
    """Every translation-answer file (any *.json under translate_answers/,
    including round-tagged deltas like 'signalisation.delta.json')."""
    return sorted(glob.glob(os.path.join(ANSWERS_DIR, "**", "*.json"), recursive=True))


def _translated_qids() -> set:
    """FR qids that already have a translation on disk — emit skips these so a
    re-run only drafts the delta and never re-touches the approved EN set."""
    done = set()
    for f in _answer_files():
        d = json.load(open(f, encoding="utf-8"))
        done |= set(d if isinstance(d, dict) else {x["qid"]: x for x in d})
    return done


def cmd_emit(*_):
    conn = qschema.connect(QDB_PATH)
    done = _translated_qids()
    jobs: dict[str, list] = {}
    for q in _fr_exportable(conn):
        if q.id in done:                 # already translated — skip (incremental)
            continue
        jobs.setdefault(q.theme, []).append({
            "qid": q.id, "stem": q.stem,
            "choices": [c.text for c in q.choices],   # order preserved
            "explanation": q.explanation})
    os.makedirs(ANSWERS_DIR, exist_ok=True)
    with open(JOBS, "w", encoding="utf-8") as fh:
        json.dump(jobs, fh, ensure_ascii=False, indent=2)
    total = sum(len(v) for v in jobs.values())
    for theme, qs in jobs.items():
        print(f"  {theme:18} {len(qs)} questions")
    print(f"→ {JOBS}  ({total} untranslated; {len(done)} already done)")


def cmd_ingest(*_):
    conn = qschema.connect(QDB_PATH)
    fr = {q.id: q for q in _fr_exportable(conn)}
    existing_en = {q.id for q in qschema.load_questions(conn) if q.lang == TGT_LANG}
    out: list[Question] = []
    stats = {"translated": 0, "kept": 0, "invalid": 0, "missing_original": 0,
             "arity": 0, "already_in_bank": 0}
    # Glob every answer file (original per-theme + any delta files) and merge.
    merged: dict[str, dict] = {}
    for path in _answer_files():
        data = json.load(open(path, encoding="utf-8"))
        merged.update(data if isinstance(data, dict) else {x["qid"]: x for x in data})
    for qid, tr in merged.items():
        stats["translated"] += 1
        orig = fr.get(qid)
        if orig is None:
            stats["missing_original"] += 1
            continue
        tchoices = tr["choices"]
        if len(tchoices) != len(orig.choices):     # arity must match the original
            stats["arity"] += 1
            continue
        # Structure (order, is_correct, image) from the ORIGINAL; text from translation.
        choices = [Choice(text=tchoices[i].strip(), image=orig.choices[i].image,
                          is_correct=orig.choices[i].is_correct)
                   for i in range(len(orig.choices))]
        q = Question(
            id=make_question_id(orig.provenance.unit_id, tr["stem"], "en"),
            theme=orig.theme, kind=orig.kind, stem=tr["stem"].strip(),
            lang=TGT_LANG, choices=choices, polarity=orig.polarity,
            image=orig.image, points=orig.points,
            explanation=tr.get("explanation", "").strip(),
            review_status="pending", distractor_strategy=orig.distractor_strategy,
            generator=GENERATOR, provenance=orig.provenance)
        if q.id in existing_en:        # already in the bank — don't reset its status
            stats["already_in_bank"] += 1
            continue
        if qschema.validate(q):
            stats["invalid"] += 1
            continue
        out.append(q)
        stats["kept"] += 1
    qschema.write_questions(conn, out)
    print(f"→ {stats['kept']} new pending EN written. {stats}")
    print("  review queue:", qschema.counts_by_status(conn))


def cmd_verify_emit(*_):
    """Pair each EN translation with its FR original, straight from the answers
    files. The EN id is recomputed exactly as ingest does, so verify-apply can
    approve it by id."""
    conn = qschema.connect(QDB_PATH)
    fr = {q.id: q for q in _fr_exportable(conn)}
    # Only verify EN drafts that are still pending — the already-approved set is
    # locked in (and recovered from translate_verdicts/), so re-verifying it is waste.
    pending_en = {q.id for q in qschema.load_questions(conn)
                  if q.lang == TGT_LANG and q.review_status == "pending"}
    out = []
    for path in _answer_files():
        theme = os.path.splitext(os.path.basename(path))[0]
        data = json.load(open(path, encoding="utf-8"))
        items = data if isinstance(data, dict) else {x["qid"]: x for x in data}
        for fr_qid, tr in items.items():
            o = fr.get(fr_qid)
            if o is None:
                continue
            en_id = make_question_id(o.provenance.unit_id, tr["stem"].strip(), "en")
            if en_id not in pending_en:        # skip already-approved EN
                continue
            out.append({
                "qid": en_id, "theme": theme,
                "fr": {"stem": o.stem, "choices": [c.text for c in o.choices],
                       "explanation": o.explanation},
                "en": {"stem": tr["stem"], "choices": tr["choices"],
                       "explanation": tr.get("explanation", "")},
                "correct_idx": o.correct})
    os.makedirs(VERDICTS_DIR, exist_ok=True)
    with open(VERIFY, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
    print(f"→ {VERIFY} ({len(out)} pairs to verify)")


def cmd_verify_apply(*_):
    merged = {}
    for f in glob.glob(os.path.join(VERDICTS_DIR, "*.json")):
        merged.update(json.load(open(f, encoding="utf-8")))
    conn = qschema.connect(QDB_PATH)
    passed = [q for q, v in merged.items() if str(v).lower().startswith("pass")]
    n = qschema.set_review_status(conn, passed, "approved")
    print(f"  approved {n} faithful translations ({len(merged) - len(passed)} left pending)")
    print("  review queue:", qschema.counts_by_status(conn))


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    fns = {"emit": cmd_emit, "ingest": cmd_ingest,
           "verify-emit": cmd_verify_emit, "verify-apply": cmd_verify_apply}
    if cmd not in fns:
        sys.exit(f"usage: python tools/subagent_translate.py {{{'|'.join(fns)}}}")
    fns[cmd]()


if __name__ == "__main__":
    main()
