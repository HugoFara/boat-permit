"""Tests for the derived-vs-official validator (`src/validate.py`).

Both instruments run fully offline here: `load_bank` is monkeypatched with synthetic
questions, so the real logic under test is exercised — scope classification, concept
matching, the absent-track suppression, gap detection, and the divergence flagger
with an injected fake adjudicator (no Anthropic call). The concept *keyword* tuning
is a living heuristic, not pinned here; the structural guarantees are.

Run with `python tests/test_validate.py`.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import validate                                        # noqa: E402
from src.questions.schema import Question, Choice, Provenance   # noqa: E402


def _q(theme, stem, correct="right", block="", qid=None, principle=""):
    return Question(
        id=qid or f"{theme}-{abs(hash(stem)) % 10000}", theme=theme, kind="rule_mc",
        stem=stem, block=block, principle=principle,
        choices=[Choice(correct, is_correct=True), Choice("wrong")],
        provenance=Provenance(unit_id="u", ref="", source="", url=""))


# A tiny synthetic world. DE is the official catalogue; CH is inland-only (no
# maritime track); FR has both tracks.
_BANKS = {
    "DE": [
        _q("schifffahrtszeichen", "Was bedeutet die blaue Tafel?", block="spezifisch_binnen"),
        _q("schifffahrtszeichen", "Was bedeutet diese Tonne im Fahrwasser?", block="spezifisch_binnen"),
        _q("verkehrsregeln", "Ein Fahrzeug will überholen.", block="spezifisch_see"),
        _q("seemannschaft", "Wie heißt dieser Knoten (Palstek)?"),
    ],
    "CH": [                                       # inland-only: no colregs at all
        _q("signalisation", "Que signifie cette bouée dans le chenal?"),
        _q("matelotage", "Comment s'appelle ce nœud?"),
    ],
    "FR": [
        _q("balisage", "Que signifie ce panneau bleu?"),    # has blue_board
        _q("regles_route", "Un navire rattrapant un autre en mer."),  # overtaking colregs
    ],
}


def _install(banks=_BANKS, monkeypatch_target=validate):
    monkeypatch_target.load_bank = lambda code: list(banks.get(code, []))


def test_coverage_counts_and_absent_track():
    orig = validate.load_bank
    try:
        _install()
        rep = validate.coverage(derived=("CH", "FR"))
        # CH implements no maritime track → reported absent, not gap-flagged.
        assert {"bank": "CH", "base": "colregs"} in rep["absent_tracks"]
        ch_colregs_gaps = [g for g in rep["gaps"]
                           if g["bank"] == "CH" and g["base"] == "colregs"]
        assert ch_colregs_gaps == []                # suppressed for the absent track
    finally:
        validate.load_bank = orig


def test_coverage_flags_a_real_gap():
    orig = validate.load_bank
    try:
        _install()
        rep = validate.coverage(derived=("CH", "FR"))
        # DE tests `blue_board` (cevni); CH's inland bank has none → a genuine gap.
        gap_concepts = {(g["bank"], g["concept"]) for g in rep["gaps"]}
        assert ("CH", "blue_board") in gap_concepts
        # FR *does* cover blue_board ("panneau bleu") → not a gap for FR.
        assert ("FR", "blue_board") not in gap_concepts
    finally:
        validate.load_bank = orig


# A principle-tagged world for the bounded-coverage instrument. DE (official) tests
# two inland topics — iala-buoyage (×2) and give-way (×1) — plus one untagged item;
# CH covers buoyage but not give-way.
_PRINC_BANKS = {
    "DE": [
        _q("schifffahrtszeichen", "Laterale Tonne A", block="spezifisch_binnen",
           principle="iala-buoyage", qid="de1"),
        _q("schifffahrtszeichen", "Laterale Tonne B", block="spezifisch_binnen",
           principle="iala-buoyage", qid="de2"),
        _q("verkehrsregeln", "Vorfahrt beim Kreuzen", block="spezifisch_binnen",
           principle="give-way", qid="de3"),
        _q("verkehrsregeln", "Eine allgemeine Regel ohne Stichwort",
           block="spezifisch_binnen", principle="", qid="de4"),  # untagged → unmeasured
    ],
    "CH": [
        _q("signalisation", "Marque laterale dans le chenal",
           principle="iala-buoyage", qid="ch1"),
    ],
}


def test_instrumentation_reports_measured_fraction():
    orig = validate.load_bank
    try:
        _install(_PRINC_BANKS)
        rep = validate.coverage(derived=("CH",))
        instr = rep["instrumentation"]["cevni"]
        # 3 of the 4 official inland questions are topic-tagged → 75% measurable.
        assert instr["official"] == 4
        assert instr["instrumented"] == 3
        assert instr["pct"] == 75.0
    finally:
        validate.load_bank = orig


def test_principle_coverage_is_weighted_and_bounded():
    orig = validate.load_bank
    try:
        _install(_PRINC_BANKS)
        rep = validate.coverage(derived=("CH",))
        cev = rep["principle_cov"]["CH"]["cevni"]
        # CH covers iala-buoyage (2 official) but not give-way (1 official):
        # 1 of 2 topics, 2 of 3 weighted → 66.7%, give-way flagged missing.
        assert cev["topics_covered"] == 1 and cev["topics_official"] == 2
        assert cev["weighted_covered"] == 2 and cev["weighted_official"] == 3
        assert cev["pct"] == round(100 * 2 / 3, 1)
        assert cev["missing"] == ["give-way"]
    finally:
        validate.load_bank = orig


def test_coverage_summary_shape():
    orig = validate.load_bank
    try:
        _install(_PRINC_BANKS)
        s = validate.coverage_summary(generated="2026-01-01")
        assert s["official"] == "DE" and s["generated"] == "2026-01-01"
        assert "DE" not in s["banks"]          # the yardstick is never self-scored
        ch = s["banks"]["CH"]["tracks"]["cevni"]
        assert ch["pct"] == 67                 # round(66.7)
        assert ch["missing"] == ["give-way"]
        assert ch["instrumented_pct"] == 75    # 3 of 4 official inland Qs are tagged
    finally:
        validate.load_bank = orig


def test_principle_coverage_skips_absent_track():
    orig = validate.load_bank
    try:
        _install()  # default world: DE has a colregs item, CH is inland-only
        rep = validate.coverage(derived=("CH", "FR"))
        # CH implements no maritime track, so it must not be scored on colregs.
        assert "colregs" not in rep["principle_cov"]["CH"]
    finally:
        validate.load_bank = orig


def test_flagger_emits_only_non_consistent_verdicts():
    orig = validate.load_bank
    try:
        _install()
        # Fake adjudicator: everything diverges → every matched pair is flagged.
        flags = validate.flag_divergences(
            "FR", base="colregs", limit=10,
            adjudicator=lambda prompt: {"verdict": "diverges", "reason": "test"})
        assert flags and all(f["verdict"] == "diverges" for f in flags)
        assert all(f["bank"] == "FR" for f in flags)

        # A "consistent" adjudicator flags nothing.
        clean = validate.flag_divergences(
            "FR", base="colregs", limit=10,
            adjudicator=lambda prompt: {"verdict": "consistent", "reason": "ok"})
        assert clean == []
    finally:
        validate.load_bank = orig


def test_flagger_respects_limit_and_dry_run():
    orig = validate.load_bank
    try:
        _install()
        seen = []
        # on_prompt path must not call the adjudicator (dry-run) and must honour limit.
        validate.flag_divergences("FR", base="colregs", limit=1,
                                  on_prompt=seen.append)
        assert len(seen) <= 1
    finally:
        validate.load_bank = orig


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")
