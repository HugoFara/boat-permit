"""Tests for the GIFT (Moodle) exporter (`tools/gift.py`).

Builds a tiny in-memory bank and checks the format invariants Moodle relies on:
single-answer questions use `=`/`~`, multi-answer questions use weighted
`~%50%`/`~%-100%` (correct weights summing to 100), control characters are
escaped, a `$CATEGORY` is emitted per theme, and figures are embedded as base64
`data:` URIs so the file is self-contained.

Run with `python tests/test_gift.py`.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import gift                                  # noqa: E402
from src.questions.schema import Question, Choice, Provenance  # noqa: E402


def _q(qid, theme, kind, stem, choices, expl="", prov=None, image=None):
    return Question(id=qid, theme=theme, kind=kind, stem=stem, lang="fr",
                    choices=choices, explanation=expl, review_status="approved",
                    generator="seed:test", image=image,
                    provenance=prov or Provenance(unit_id="u", ref="ONI art. 1",
                        source="ONI (RS 747.201.1)", url="https://x.test/a#art_1",
                        as_of="2022-01-01", licence="public-domain"))


def test_escape():
    assert gift._esc("a=b~c#d{e}f:g") == "a\\=b\\~c\\#d\\{e\\}f\\:g"
    assert gift._esc("back\\slash") == "back\\\\slash"


def test_single_answer_uses_equals_and_tilde():
    q = _q("q-1", "signalisation", "rule_mc", "Feu rouge ?",
           [Choice("Stop", is_correct=True), Choice("Go"), Choice("Slow")],
           expl="Rouge = stop.")
    block = gift._render(q)
    assert block.startswith("::q-1:: [html]")
    assert "=Stop" in block
    assert "~Go" in block and "~Slow" in block
    assert "~%" not in block                       # single answer → no weights
    # explanation is escaped in general feedback (the '=' becomes '\\=')
    assert "####[html]" in block and "Rouge \\= stop." in block
    # source link present and escaped (Moodle restores it)
    assert "<a href\\=" in block


def test_multi_answer_weights_sum_to_100():
    q = _q("q-2", "meteorologie", "meteo_mc", "Lesquelles ?",
           [Choice("A", is_correct=True), Choice("B", is_correct=True),
            Choice("C")])
    block = gift._render(q)
    assert "~%50%A" in block and "~%50%B" in block   # 2 correct → 50% each
    assert "~%-100%C" in block                       # wrong → -100%
    assert "=A" not in block                         # multi never uses '='


def test_pct_helper():
    assert gift._pct(1) == "100"
    assert gift._pct(2) == "50"
    assert gift._pct(4) == "25"
    assert gift._pct(3) == "33.33333"


def test_image_is_embedded_as_data_uri():
    # use a real bundled asset so the data URI is genuine
    img = "data/assets/oni/image39.png"
    assert os.path.exists(os.path.join(gift.BASE, img)), "fixture asset missing"
    q = _q("q-3", "signalisation", "figure_recognition", "Ce signal ?",
           [Choice("X", is_correct=True), Choice("Y")], image=img)
    block = gift._render(q)
    assert "[html]" in block
    assert "data\\:image/png;base64," in block       # escaped data URI, embedded
    assert "base64,A" in block or "base64," in block  # has payload


def test_file_has_category_per_theme():
    qs = [
        _q("q-a", "signalisation", "rule_mc", "S1?",
           [Choice("a", is_correct=True), Choice("b")]),
        _q("q-b", "meteorologie", "meteo_mc", "M1?",
           [Choice("a", is_correct=True), Choice("b")]),
    ]
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "out.gift")
        gift._write_gift(qs, "fr", p)
        text = open(p, encoding="utf-8").read()
    assert "$CATEGORY: Permis bateau · Léman (FR)/Signalisation" in text
    assert "$CATEGORY: Permis bateau · Léman (FR)/Météorologie" in text
    # both questions rendered, separated by blank lines
    assert text.count("::q-") == 2


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
    print(f"\n{len(tests)} tests passed")
