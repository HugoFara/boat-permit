"""Tests for the German exam-theme tagger (`src/countries/de_themes.py`).

Same contract as the Swiss tagger (`tests` over `src.themes`): an anchored
definitions check wins first, then high-precision German keyword rules, with a
sensible legal fallback. These pin a few representative classifications so a rule
edit that breaks them is caught.

Run with `python tests/test_de_themes.py`.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.countries import de_themes as T               # noqa: E402


def test_definitions_detected_structurally():
    assert T.tag_theme(title="Begriffsbestimmungen", text="…") == "definitionen"
    assert T.tag_theme(text="Im Sinne dieser Verordnung sind Sportboote …") == "definitionen"


def test_representative_keyword_routing():
    cases = {
        "verkehrsregeln": "Vorfahrt und Ausweichregeln beim Begegnen",
        "schifffahrtszeichen": "Die Backbordtonne markiert die Fahrwasserseite",
        "lichter_signale": "Lichterführung: Toplicht, Hecklicht und ein Schallsignal",
        "wetterkunde": "Die Windstärke nach Beaufort und eine Sturmwarnung",
        "gezeiten": "Ebbe und Flut bestimmen den Tidenhub",
        "seemannschaft": "Der Palstek ist ein Knoten zum Festmachen",
        "umweltschutz": "Gewässerschutz: kein Öl einleiten",
        "navigation": "Kartenkurs und Missweisung auf der Seekarte",
        "recht_dokumente": "Der Sportbootführerschein und die Zulassung",
    }
    for theme, text in cases.items():
        got = T.tag_theme(text=text)
        assert got == theme, f"{text!r} -> {got!r}, expected {theme!r}"


def test_lights_beat_traffic_when_both_present():
    # a lights article that also mentions courses must stay in lichter_signale
    got = T.tag_theme(title="Lichterführung", text="Fahrzeuge zeigen ein Toplicht beim Kurs")
    assert got == "lichter_signale"


def test_default_fallback_is_legal():
    assert T.tag_theme(text="Ein Satz ganz ohne einschlägige Stichwörter.") == "recht_dokumente"
    assert T.tag_theme(text="irrelevant", default="verkehrsregeln") == "verkehrsregeln"


def test_permit_theme_sets_are_valid():
    for code, ts in de_themes_permit_items():
        for t in ts:
            assert T.is_valid(t), f"{code}: invalid theme {t!r}"


def de_themes_permit_items():
    return T.PERMIT_THEMES.items()


def test_bodensee_theme_block_map_is_consistent():
    # Every theme that maps to a Bodensee block uses a real DE theme and a block id
    # that the name->id map also yields (so questions and the exam structure agree).
    ids = set(T.BODENSEE_BLOCK_NAME_TO_ID.values())
    for theme, bid in T._BODENSEE_BLOCK_BY_THEME.items():
        assert T.is_valid(theme), f"unknown theme {theme!r}"
        assert bid in ids, f"theme {theme!r} -> {bid!r} not in BODENSEE_BLOCK_NAME_TO_ID"
    assert T.bodensee_block_for("recht_dokumente") == "bodensee_allgemeines"
    assert T.bodensee_block_for("__none__") == ""


def test_bodensee_permits_resolve_to_block_ids():
    # Both Bodensee permits' exam-block names must be in the name->id map, else
    # run._de_block_rules silently drops them from the web player's permit picker.
    from src.countries import de
    for code in ("Bodensee-A", "Bodensee-D"):
        for blk in de.PERMITS[code].exam.blocks:
            assert blk.name in T.BODENSEE_BLOCK_NAME_TO_ID, \
                f"{code}: block {blk.name!r} has no id"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
    print(f"\n{len(tests)} tests passed")
