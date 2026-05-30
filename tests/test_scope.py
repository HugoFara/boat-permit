"""Tests for the question-scope classifier (`src/scope.py`).

Scope places each question on the lex-specialis hierarchy: portable seamanship is
`universal`, the harmonised inland traffic code is `cevni`, the maritime one is
`colregs`, country statute / frontier waters are `national`, and water-body
specifics (named winds, an excluded regime) are `local`. These checks pin that
taxonomy so the per-base core bundles stay clean.

Run with `python tests/test_scope.py`.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import scope                                   # noqa: E402
from src.questions.schema import Question, Choice, Provenance  # noqa: E402


def _q(theme, stem="", ref="", source="", qid="t"):
    """A minimal Question for classification (classify reads theme + ref/source/
    stem only; the choices/ids are placeholders)."""
    return Question(id=qid, theme=theme, kind="rule_mc", stem=stem,
                    choices=[Choice("a", is_correct=True), Choice("b")],
                    provenance=Provenance(unit_id="u", ref=ref, source=source, url=""))


def test_scopes_vocabulary():
    assert scope.SCOPES == {"universal", "cevni", "colregs", "national", "local"}
    assert set(scope.BASES) == {"universal", "cevni", "colregs"}
    assert set(scope.OVERLAYS) == {"national", "local"}
    assert scope.DEFAULT_SCOPE in scope.SCOPES


def test_classify_always_returns_a_valid_scope():
    for theme in ("signalisation", "lois", "meteorologie", "matelotage",
                  "definitions", "voile", "eaux_frontalieres", "unknown_theme"):
        assert scope.classify(_q(theme, "texte quelconque")) in scope.SCOPES


def test_harmonised_inland_signage_is_cevni():
    assert scope.classify(_q("signalisation", "Que signifie ce panneau ?")) == "cevni"


def test_maritime_signage_is_colregs():
    # Sea buoyage/lights are COLREGS, not CEVNI — the inland/sea split.
    assert scope.classify(_q("signalisation", "Feux de navigation en mer la nuit")) == "colregs"
    assert scope.classify(_q("lois", "règle de barre selon le RIPAM")) == "colregs"
    assert scope.classify(_q("signalisation", "Seezeichen auf Seeschifffahrtsstraßen")) == "colregs"


def test_universal_seamanship_splits_out_of_cevni():
    # Knots, definitions, sailing handling and generic weather are portable on any
    # water under any code — universal, NOT the CEVNI traffic code.
    for theme in ("matelotage", "definitions", "voile"):
        assert scope.classify(_q(theme, "contenu portable")) == "universal"
    assert scope.classify(_q("meteorologie", "formation des nuages et des fronts")) == "universal"


def test_frontier_waters_are_national():
    assert scope.classify(_q("eaux_frontalieres", "règle sur le lac")) == "national"
    assert scope.classify(_q("lois", "selon la convention franco-suisse")) == "national"


def test_local_meteo_vs_universal():
    assert scope.classify(_q("meteorologie", "la bise s'établit sur le Léman")) == "local"
    assert scope.classify(_q("meteorologie", "la vaudaire")) == "local"


def test_national_statute_within_lois():
    assert scope.classify(_q("lois", "couverture d'assurance-responsabilité civile exigée")) == "national"
    # a genuine harmonised inland navigation rule stays cevni
    assert scope.classify(_q("lois", "croisement et dépassement des bateaux")) == "cevni"


def test_excluded_regime_is_guarded_out_of_the_core():
    # A harmonised-looking signalisation question tied to the non-CEVNI Bodensee
    # regime (BSO) — must NOT be classified into any base.
    q = _q("signalisation", "Que signifie ce signal ?",
           ref="BSO Annexe", source="Bodensee-Schifffahrts-Ordnung")
    assert scope.classify(q) == "local"
    assert q not in scope.core_bank([q])


def test_core_bank_is_the_union_of_bases():
    qs = [
        _q("signalisation", "panneau"),               # cevni
        _q("signalisation", "feu de mer en mer"),     # colregs
        _q("matelotage", "nœud de chaise"),           # universal
        _q("eaux_frontalieres", "frontière"),         # national
        _q("meteorologie", "la vaudaire"),            # local
    ]
    core = scope.core_bank(qs)
    assert all(scope.classify(q) in scope.BASES for q in core)
    assert len(core) == 3                              # cevni + colregs + universal
    assert all(q in qs for q in core)                  # a strict subset, nothing invented


def test_ids_by_base_partitions_the_portable_set():
    qs = [_q("signalisation", "panneau", qid="a"),         # cevni
          _q("lois", "barre RIPAM en mer", qid="b"),       # colregs
          _q("definitions", "terme", qid="c"),             # universal
          _q("eaux_frontalieres", "x", qid="d")]           # national (not a base)
    by = scope.ids_by_base(qs)
    assert by["cevni"] == {"a"} and by["colregs"] == {"b"} and by["universal"] == {"c"}
    assert scope.bases_present(qs) == ["universal", "cevni", "colregs"]


def test_scope_counts_partition_the_input():
    qs = [_q("signalisation"), _q("eaux_frontalieres"), _q("meteorologie", "joran"),
          _q("matelotage")]
    counts = scope.scope_counts(qs)
    assert set(counts) == scope.SCOPES
    assert sum(counts.values()) == len(qs)
    assert counts["cevni"] == 1 and counts["national"] == 1
    assert counts["local"] == 1 and counts["universal"] == 1


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
    print(f"\n{len(tests)} tests passed")
