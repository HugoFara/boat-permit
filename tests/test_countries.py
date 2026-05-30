"""Tests for the country dimension (`src/countries/`) + its tie-in to the
descriptive `src/jurisdictions/` registry.

The country layer is the build-time ingestion config (sources, tagger, themes,
permits, regions) that the fetch→parse→normalize pipeline consumes. These checks
pin the contract: the registry is well-formed, the CH country re-exports the
original flat modules verbatim (so the Swiss build is unchanged), Germany is
registered with valid gii law sources + a coherent permit/theme/region model, and
the jurisdictions layer learns about Germany.

Run with `python tests/test_countries.py`.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import cantons, countries, jurisdictions, sources, themes   # noqa: E402
from src.countries import ch, de, de_themes, intl, intl_themes        # noqa: E402


def test_registry_well_formed():
    assert set(countries.codes()) >= {"CH", "DE"}
    assert countries.get("de").code == "DE"
    assert countries.get(None).code == countries.DEFAULT == "INT"
    try:
        countries.get("ZZ")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for unknown country")


def test_ch_reexports_existing_modules_unchanged():
    c = ch.COUNTRY
    assert c.code == "CH" and c.default_lang == "fr"
    assert c.sources == tuple(sources.SOURCES)        # same Source objects
    assert c.themes == dict(themes.THEMES)
    assert c.tagger is themes.tag_theme
    assert c.extension_themes == themes.EXTENSION_THEMES
    assert set(c.regions) == set(cantons.CANTONS)     # cantons -> regions
    assert c.default_region == cantons.DEFAULT_CANTON
    assert set(c.permits) == set(("A", "D"))


def test_de_sources_are_law_with_clean_provenance():
    c = de.COUNTRY
    assert c.code == "DE" and c.default_lang == "de" and c.langs == ("de",)
    assert c.sources, "Germany must register law sources"
    for s in c.sources:
        assert s.default_theme in c.themes
        if s.kind == "gii":
            assert s.gii_slug, f"{s.id} needs a gesetze-im-internet slug"
        elif s.kind == "fedlex":
            assert s.eli, f"{s.id} needs a Fedlex ELI fragment"
        else:
            raise AssertionError(f"{s.id}: unexpected source kind {s.kind!r}")
    by_kind = {s.id: s.kind for s in c.sources}
    # the gii federal spine ...
    assert {"seeschstro", "binschstro", "kvr", "spfv"} <= set(by_kind)
    assert all(by_kind[i] == "gii" for i in ("seeschstro", "binschstro", "kvr", "spfv"))
    # ... plus the Bodensee-Schifffahrts-Ordnung via Fedlex (SR 747.223.1), the
    # public-domain grounding for the law-seeded Bodensee question set.
    assert by_kind.get("bso") == "fedlex"


def test_de_permits_cover_the_chosen_scope():
    p = de.COUNTRY.permits
    assert {"SBF-See", "SBF-Binnen-Motor", "SKS", "SSS", "SHS",
            "Bodensee-A", "Bodensee-D"} <= set(p)
    # the mandatory federal SBF vs the voluntary higher certs
    assert p["SBF-See"].mandatory and p["SBF-Binnen-Motor"].mandatory
    assert not p["SKS"].mandatory and not p["SSS"].mandatory


def test_permit_themes_are_valid_for_every_country():
    for c in countries.COUNTRIES.values():
        for code, permit in c.permits.items():
            for t in permit.themes:
                assert t in c.themes, f"{c.code}/{code}: unknown theme {t!r}"


def test_block_counts_sum_to_question_total():
    # where a German permit defines both a question count and blocks, the blocks
    # must partition the paper exactly (e.g. SBF Binnen Motor: 7 + 23 = 30).
    for code, permit in de.COUNTRY.permits.items():
        e = permit.exam
        if e.questions and e.blocks:
            assert sum(b.count for b in e.blocks) == e.questions, \
                f"{code}: blocks {[b.count for b in e.blocks]} != {e.questions}"


def test_de_regions_and_references():
    c = de.COUNTRY
    assert set(c.regions) == {"national", "bodensee"}
    assert c.default_region == "national"
    assert c.regions["national"].primary and not c.regions["bodensee"].primary
    # the §5 catalogue finding is recorded as references (documented, not ingested)
    assert any("Fragenkatalog" in r.name for r in c.references)
    assert c.region_manifest()[0]["code"] == "national"   # primary first


def test_de_tagger_is_the_de_themes_tagger():
    assert de.COUNTRY.tagger is de_themes.tag_theme


def test_int_is_a_sourcing_only_universal_layer():
    c = intl.COUNTRY
    assert c.code == "INT" and c.default_lang == "en" and c.langs == ("en",)
    # No permits / no playable bank — this layer only grounds the harmonised bases.
    assert c.permits == {}
    assert c.tagger is intl_themes.tag_theme
    # COLREG is ingested as a public-domain PDF (USCG); every source is valid.
    by_kind = {s.id: s.kind for s in c.sources}
    assert by_kind.get("colreg") == "pdf"
    for s in c.sources:
        assert s.default_theme in c.themes
        assert s.kind == "pdf" and s.url and s.lang == "en"
    # CEVNI is documented but NOT ingested (UN licence barrier).
    assert any("CEVNI" in r.name for r in c.references)
    assert all("cevni" != s.id for s in c.sources)


def test_int_contributes_no_national_jurisdiction_node():
    # The supra-national layer is a base, not a national implementer: it must not
    # spawn INT-INLAND / INT-MARITIME regime nodes in the jurisdictions tree.
    codes = jurisdictions.codes()
    assert "INT-INLAND" not in codes and "INT-MARITIME" not in codes
    # The harmonised bases it grounds still exist.
    assert {"UNIVERSAL", "CEVNI", "COLREGS"} <= set(codes)


def test_pdf_is_a_registered_source_kind():
    # The COLREG PDF path must be wired in both fetch and parse dispatch tables.
    from src import fetch, parse as parse_stage
    assert "pdf" in fetch._DISPATCH
    assert "pdf" in parse_stage._PARSERS
    assert "pdf" not in fetch._PER_LANG_KINDS      # single-language, like html


def test_subagent_paths_uniform_per_country():
    # Every country is namespaced uniformly under countries/<code>/ (base lang
    # directly there, others under <lang>/) — no country is privileged with a flat
    # root, and a country code can never collide with a language dir.
    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
    import subagent_draft as sd
    rstrip = lambda p: p.rstrip(os.sep)
    ch_fr = rstrip(sd._paths("fr", countries.get("CH"))["answers"])   # base lang
    ch_de = rstrip(sd._paths("de", countries.get("CH"))["answers"])   # non-base lang
    de_de = rstrip(sd._paths("de", countries.get("DE"))["answers"])
    int_en = rstrip(sd._paths("en", countries.get("INT"))["answers"])
    assert ch_fr.endswith(os.path.join("countries", "ch"))            # CH no longer flat
    assert ch_de.endswith(os.path.join("countries", "ch", "de"))
    assert de_de.endswith(os.path.join("countries", "de"))
    assert int_en.endswith(os.path.join("countries", "int"))
    # No country maps to a bare draft_answers/ root or a bare lang dir.
    for p in (ch_fr, ch_de, de_de, int_en):
        assert os.path.join("draft_answers", "countries") in p


def test_no_country_gets_an_unprefixed_bank():
    # The CH-privileged unprefixed names (questions.sqlite / kb.sqlite) are gone:
    # every country's bank/KB is namespaced by code.
    import run
    assert run._qpaths("CH")[0].endswith("questions.ch.sqlite")
    assert run._kbpaths("CH")[0].endswith("kb.ch.sqlite")
    assert run._qpaths("INT")[0].endswith("questions.int.sqlite")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
    print(f"\n{len(tests)} tests passed")
