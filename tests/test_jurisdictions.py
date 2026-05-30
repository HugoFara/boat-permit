"""Tests for the regime tree (`src/jurisdictions.py`).

Jurisdictions form a single tree ordered by applicability (lex specialis): the
bases UNIVERSAL → {CEVNI, COLREGS}, then country regimes derived per track from
`src/countries`, then shared waters. These checks pin that the tree is well-formed
(every non-root refines a real parent), that country nodes are derived (not
duplicated) per track, that the special waters carry the right relation, and that
the excluded-regime guard recognises Bodensee.

Run with `python tests/test_jurisdictions.py`.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import jurisdictions, countries                # noqa: E402


def test_bases_are_the_roots_and_form_universal_to_codes():
    u = jurisdictions.get("UNIVERSAL")
    assert u.kind == "base" and u.refines == "" and u.relation == "is_base"
    for code in ("CEVNI", "COLREGS"):
        b = jurisdictions.get(code)
        assert b.kind == "base" and b.refines == "UNIVERSAL" and b.relation == "is_base"
    assert jurisdictions.track("CEVNI") == "inland"
    assert jurisdictions.track("COLREGS") == "maritime"


def test_tree_is_well_formed_every_non_root_refines_a_real_parent():
    for code in jurisdictions.codes():
        j = jurisdictions.get(code)
        assert j.kind in jurisdictions.KINDS
        assert j.relation in jurisdictions.RELATIONS
        if code == "UNIVERSAL":
            assert j.refines == ""
        else:
            assert j.refines in jurisdictions.REGISTRY      # parent exists
    # the root is reachable from every node
    for code in jurisdictions.codes():
        assert jurisdictions.ancestors(code)[-1:] in ([], ["UNIVERSAL"])
        assert jurisdictions.base_of(code) in ("UNIVERSAL", "CEVNI", "COLREGS")


def test_country_regimes_are_derived_per_track():
    # Switzerland is inland-only; its regime derives from the CH country and sits
    # under CEVNI.
    ch = jurisdictions.get("CH-INLAND")
    assert ch.kind == "national" and ch.derives_from == "CH"
    assert ch.refines == "CEVNI" and ch.track == "inland"
    assert ch.name.startswith(countries.get("CH").name)     # one source of truth
    assert jurisdictions.base_of("CH-INLAND") == "CEVNI"


def test_a_country_with_sea_permits_gets_a_maritime_regime():
    # France has an inland option (eaux intérieures) AND a sea option (côtière),
    # so it must yield both an inland (CEVNI) and a maritime (COLREGS) regime.
    fr_codes = [c for c in jurisdictions.codes()
                if jurisdictions.get(c).derives_from == "FR"]
    bases = {jurisdictions.base_of(c) for c in fr_codes}
    assert bases == {"CEVNI", "COLREGS"}, f"FR regimes: {fr_codes}"
    assert jurisdictions.get("FR-MARITIME").track == "maritime"


def test_bodensee_is_excluded_and_replaces_its_base():
    b = jurisdictions.get("bodensee")                       # case-insensitive
    assert b.kind == "shared_water" and b.relation == "excluded"
    assert b.refines == "CEVNI"                             # sits under inland, but…
    assert {"CH", "DE", "AT"} <= set(b.members)
    assert "BODENSEE" in jurisdictions.excluded_codes()


def test_rhine_and_leman_diverge_but_stay_in_the_core():
    for code in ("RHINE", "LEMAN"):
        j = jurisdictions.get(code)
        assert j.kind == "shared_water" and j.relation == "diverges"
        assert code not in jurisdictions.excluded_codes()   # divergence ≠ exclusion


def test_excluded_regime_guard_recognises_bodensee_only():
    assert jurisdictions.excluded_regime("Signal selon la BSO sur le Bodensee") == "BODENSEE"
    assert jurisdictions.excluded_regime("Lac de Constance, règle locale") == "BODENSEE"
    assert jurisdictions.excluded_regime("Rhin — CCNR / RheinSchPV") is None   # diverges, not excluded
    assert jurisdictions.excluded_regime("ONI art. 2 — définitions") is None
    assert jurisdictions.excluded_regime("") is None


def test_get_defaults_and_rejects_unknown():
    assert jurisdictions.get(None).code == jurisdictions.DEFAULT
    assert jurisdictions.get("").code == jurisdictions.DEFAULT
    assert jurisdictions.DEFAULT == "UNIVERSAL"
    try:
        jurisdictions.get("ZZ")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for unknown jurisdiction")


def test_codes_order_bases_then_nationals_then_waters():
    cs = jurisdictions.codes()
    kinds = [jurisdictions.get(c).kind for c in cs]
    last_base = max(i for i, k in enumerate(kinds) if k == "base")
    first_nat = min(i for i, k in enumerate(kinds) if k == "national")
    last_nat = max(i for i, k in enumerate(kinds) if k == "national")
    first_water = min(i for i, k in enumerate(kinds) if k == "shared_water")
    assert last_base < first_nat < last_nat < first_water
    assert cs[0] == "UNIVERSAL"
    assert set(cs) >= {"UNIVERSAL", "CEVNI", "COLREGS", "CH-INLAND", "BODENSEE"}


def test_manifest_shape_for_player():
    man = jurisdictions.as_manifest()
    assert [m["code"] for m in man][0] == "UNIVERSAL"
    keys = {"code", "name", "kind", "refines", "relation", "track", "base", "members"}
    assert all(keys <= set(m) for m in man)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
    print(f"\n{len(tests)} tests passed")
