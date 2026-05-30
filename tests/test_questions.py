"""Contract tests for the Phase-2 question schema (`src/questions`).

Plain asserts, no test framework — run with `python tests/test_questions.py`.
These pin the locked decisions (multi-select answers, point-based scoring at the
official 165/180 threshold, the review-status export gate, provenance round-trip)
so the downstream generators can rely on a stable shape.
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.questions import (Question, Choice, Provenance, ExamConfig,  # noqa: E402
    make_question_id, validate, score, grade_exam,
    connect, write_questions, set_meta, export_json, load_questions)


def _prov(unit_id="u", ref="r"):
    return Provenance(unit_id=unit_id, ref=ref, source="ONI", url="https://x",
                      as_of="2022-01-01", licence="Public domain")


def _rule_q(qid, correct=(0,)):
    return Question(
        id=qid, theme="lois", kind="rule_mc", stem="s",
        choices=[Choice("a", is_correct=0 in correct),
                 Choice("b", is_correct=1 in correct),
                 Choice("c", is_correct=2 in correct)],
        provenance=_prov())


def test_validation():
    ok = _rule_q("q-ok", correct=(0,))
    assert validate(ok) == [], validate(ok)
    # two correct is legal (multi-select)
    assert validate(_rule_q("q-2", correct=(0, 1))) == []
    # zero correct, all correct, and missing provenance are rejected
    assert validate(_rule_q("q-0", correct=())) , "0-correct must fail"
    assert validate(_rule_q("q-3", correct=(0, 1, 2))), "all-correct must fail"
    fig = Question(id="q-f", theme="signalisation", kind="figure_recognition",
                   stem="?", choices=[Choice("a", is_correct=True), Choice("b")],
                   provenance=_prov())
    assert any("no image" in e for e in validate(fig)), "figure w/o image must fail"


def test_correct_property():
    assert _rule_q("q", correct=(0,)).correct == [0]
    assert _rule_q("q", correct=(0, 1)).correct == [0, 1]


def test_scoring_all_or_nothing():
    assert score([0], [0], 3, 3, "all_or_nothing") == 3.0
    assert score([1], [0], 3, 3, "all_or_nothing") == 0.0
    assert score([0, 1], [0, 1], 3, 3, "all_or_nothing") == 3.0
    assert score([0], [0, 1], 3, 3, "all_or_nothing") == 0.0   # partial miss = 0


def test_scoring_partial():
    assert score([0], [0, 1], 3, 3, "partial") == 2.0          # 2/3 judgments right
    assert score([0, 1], [0, 1], 3, 3, "partial") == 3.0


def test_pass_boundary():
    """Official: 165/180 passes; that is at most 15 fault points = 5 wrong q."""
    cfg = ExamConfig()
    qs = [_rule_q(f"q{i}", correct=(0,)) for i in range(60)]
    five_wrong = {f"q{i}": ([0] if i >= 5 else [1]) for i in range(60)}
    six_wrong = {f"q{i}": ([0] if i >= 6 else [1]) for i in range(60)}
    r5 = grade_exam(qs, five_wrong, cfg)
    r6 = grade_exam(qs, six_wrong, cfg)
    assert r5 == {"earned": 165.0, "total": 180, "pass_points": 165,
                  "fault_points": 15.0, "passed": True}, r5
    assert r6["passed"] is False and r6["earned"] == 162.0, r6


def test_persistence_and_export_gate():
    db, js = "data/_qtest.sqlite", "data/_qtest.json"
    for f in (db, js):
        if os.path.exists(f):
            os.remove(f)
    try:
        approved = _rule_q("q-app", correct=(0, 1))
        approved.review_status = "approved"
        auto = _rule_q("q-auto", correct=(0,))
        auto.review_status = "auto_approved"
        pending = _rule_q("q-pend", correct=(0,))   # LLM draft — must not export
        pending.review_status = "pending"
        conn = connect(db)
        set_meta(conn, schema="v1")
        write_questions(conn, [approved, auto, pending])
        n = export_json(conn, js, exportable_only=True)
        data = json.load(open(js))
        assert n == 2, n
        ids = {q["id"] for q in data["questions"]}
        assert ids == {"q-app", "q-auto"}, ids
        # multi-select answer survives the round trip
        back = {q.id: q for q in load_questions(conn)}
        assert back["q-app"].correct == [0, 1]
        assert len(back) == 3
        conn.close()
    finally:
        for f in (db, js):
            if os.path.exists(f):
                os.remove(f)


def test_invalid_batch_rejected():
    db = "data/_qtest2.sqlite"
    if os.path.exists(db):
        os.remove(db)
    try:
        conn = connect(db)
        try:
            write_questions(conn, [_rule_q("q-bad", correct=())])
            assert False, "write_questions must reject an invalid question"
        except ValueError as e:
            assert "invalid question" in str(e)
        conn.close()
    finally:
        if os.path.exists(db):
            os.remove(db)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
    print(f"\n{len(tests)} tests passed")
