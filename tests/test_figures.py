"""Tests for the figure-question generator's quality-critical pure logic
(`src/questions/figures.py`) — chiefly the distractor-compatibility guard that
keeps an "also-correct" or trivially-easy option out. No KB needed.

Run with `python tests/test_figures.py`.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.questions import figures as F  # noqa: E402


def test_compatible_rejects_overlap():
    # identical → not a distractor
    assert not F._compatible("Interdiction de passer", "Interdiction de passer")
    # sub/superset → "passer" vs "passer pour bateaux motorisés" could be also-correct
    assert not F._compatible("Interdiction de passer",
                             "Interdiction de passer pour bateaux motorisés")
    assert not F._compatible("Interdiction de passer pour bateaux motorisés",
                             "Interdiction de passer")
    # near-paraphrase (Jaccard ≥ 0.7) → rejected
    assert not F._compatible("Obligation de s’arrêter", "Obligation de s’arrêter ici")


def test_compatible_accepts_distinct_same_family():
    assert F._compatible("Interdiction d’ancrer", "Interdiction de stationner")
    assert F._compatible("Feu fixe visible de tous les côtés", "Feu scintillant")
    assert F._compatible("Ballon vert", "Ballon jaune")


def test_choose_two_is_distinct_and_compatible():
    ans = "Interdiction d’ancrer"
    pool = ["Interdiction d’ancrer",               # == answer, must be skipped
            "Interdiction de stationner",
            "Interdiction de passer",
            "Interdiction de passer pour bateaux motorisés"]  # superset of "passer"
    picks = F._choose_two(ans, pool, seed=1)
    assert len(picks) == 2
    assert ans not in picks
    assert len(set(picks)) == 2
    # the two picks must be mutually compatible (not sub/superset of each other)
    assert F._compatible(picks[0], picks[1])


def test_choose_two_deterministic():
    pool = ["a board", "b board", "c board", "d board", "e board"]
    assert F._choose_two("answer board", pool, seed=42) == \
        F._choose_two("answer board", pool, seed=42)


def test_signal_type():
    assert F._signal_type("Interdiction de stationner") == "interdiction"
    assert F._signal_type("Obligation de siffler") == "obligation"
    assert F._signal_type("Ballon vert") == "ballon"
    assert F._signal_type("Feu scintillant") == "feu"
    assert F._signal_type("Quelque chose d’inconnu") == "autre"


def test_recognizable_filter():
    assert F._recognizable("Interdiction de stationner")
    assert F._recognizable("Ballon vert")
    assert not F._recognizable("ONI art. 147 – figure 1")        # bare-ref fallback
    assert not F._recognizable("Annexe 14 – Calcul de franc-bord")  # annex-title fallback
    assert not F._recognizable("Bateaux motorisés; feu de mât; feu clair blanc")  # multi-clause
    assert not F._recognizable("6")                              # no real word


def test_answer_gate_admits_longer_atomic_captions():
    # A real single-meaning caption just over the distractor cap: rejected as a
    # distractor (keeps the option list tight) but admissible as an answer.
    cap = "Interdiction de naviguer en dehors des limites indiquées"  # 56 chars
    assert 55 < len(cap) <= F._ANSWER_MAXLEN
    assert not F._recognizable(cap)                       # distractor gate (<=55)
    assert F._recognizable(cap, F._ANSWER_MAXLEN)         # answer gate
    # but the widened answer gate must NOT admit semicolons or fallbacks
    assert not F._recognizable("Bateaux motorisés; feu de mât: blanc", F._ANSWER_MAXLEN)
    assert not F._recognizable("Annexe 4 – Signaux de prescription", F._ANSWER_MAXLEN)
    # nor a genuinely over-long multi-condition description
    assert not F._recognizable("x" * (F._ANSWER_MAXLEN + 1) + " mot", F._ANSWER_MAXLEN)


def test_normalize_caption():
    assert F._normalize_caption("feu scintillant") == "Feu scintillant"
    assert F._normalize_caption("Convois poussés:") == "Convois poussés"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
    print(f"\n{len(tests)} tests passed")
