"""German exam-theme taxonomy + rule-based tagger (mirrors :mod:`src.themes`).

The German SBF exams test a handful of subject areas (Sachgebiete). We tag each
ingested law unit to one of them with the same auditable approach as the Swiss
tagger: an anchored definitions check first, then ordered high-precision keyword
rules over the unit's ref/title/text, with the source default as the fallback.

Only the rule-bearing themes get units from the federal *law* (traffic rules,
marks, lights/signals, definitions, environment, licensing). The rest
(``wetterkunde``, ``seemannschaft``, ``navigation``, ``gezeiten``) are
catalogue/teaching topics with no ordinance text — they are EXTENSION themes,
scaffolded ahead of the official ELWIS question catalogue, so a law-only German
build legitimately has no units for them and the normalize stage won't warn.
"""

from __future__ import annotations

import re

# Canonical theme ids (stable keys) -> human label (German, as on the exam).
THEMES: dict[str, str] = {
    "definitionen": "Begriffsbestimmungen",
    "verkehrsregeln": "Verkehrsvorschriften und Fahrregeln",
    "schifffahrtszeichen": "Schifffahrtszeichen und Betonnung",
    "lichter_signale": "Lichter, Sichtzeichen und Schallsignale",
    "wetterkunde": "Wetterkunde",
    "seemannschaft": "Seemannschaft",
    "navigation": "Navigation",
    "gezeiten": "Gezeiten und Strömung",
    "umweltschutz": "Umweltschutz",
    "recht_dokumente": "Recht, Führerschein und Dokumente",
}

# Themes with no public-domain *law* source — they come from the official
# question catalogue / teaching material, not the ordinances. Scaffolded so a
# law-only build stays clean (see normalize's missing-theme check).
EXTENSION_THEMES: frozenset[str] = frozenset(
    {"wetterkunde", "seemannschaft", "navigation", "gezeiten"})

# Which themes each permit's exam draws on. Binnen is the inland core; See adds
# coastal navigation + tides; the higher certs (SKS/SSS/SHS) reuse the See set
# (their depth differs, not their topic list, at this granularity).
_BINNEN = ("definitionen", "verkehrsregeln", "schifffahrtszeichen",
           "lichter_signale", "seemannschaft", "umweltschutz", "recht_dokumente")
_BINNEN_SEGELN = _BINNEN + ("wetterkunde",)
_SEE = ("definitionen", "verkehrsregeln", "schifffahrtszeichen", "lichter_signale",
        "wetterkunde", "seemannschaft", "navigation", "gezeiten",
        "umweltschutz", "recht_dokumente")

PERMIT_THEMES: dict[str, tuple[str, ...]] = {
    "SBF-Binnen-Motor": _BINNEN,
    "SBF-Binnen-Segeln": _BINNEN_SEGELN,
    "SBF-Binnen-Motor-Segeln": _BINNEN_SEGELN,
    "SBF-See": _SEE,
    "SKS": _SEE,
    "SSS": _SEE,
    "SHS": _SEE,
    "Bodensee-A": _BINNEN,
    "Bodensee-D": _BINNEN_SEGELN,
}

# --- Bodensee-Schifferpatent exam blocks --------------------------------------
# The BSO-seeded prose questions feed the Bodensee theory exam's Sachgebiete (the
# official a–i structure lives in countries/de.py:_BODENSEE_ALLGEMEIN/_SEGELN).
# These ids namespace cleanly against the federal SBF block ids (basis/
# spezifisch_*), so the Bodensee and SBF pools coexist in one bank and each
# permit draws only its own blocks. Keyed by ExamBlock.name -> block id:
BODENSEE_BLOCK_NAME_TO_ID: dict[str, str] = {
    "Allgemeines, Zulassung, Bau und Ausrüstung": "bodensee_allgemeines",
    "Schallzeichen, Lichterführung, optische Signale": "bodensee_signale",
    "Schifffahrtszeichen": "bodensee_zeichen",
    "Ausweich- und Fahrregeln": "bodensee_fahrregeln",
    "Umweltschutz und Seemannschaft": "bodensee_umwelt_seemannschaft",
    "Wetterkunde und Navigation": "bodensee_wetter_navigation",
    "Rheinstrecke (Alter Rhein/Seerhein)": "bodensee_rhein",
    "Segeln allgemein": "bodensee_segeln_allgemein",
    "Segeln Fahrregeln": "bodensee_segeln_fahrregeln",
}

# Which Bodensee Sachgebiet a prose question lands in, by its German theme. The
# Rheinstrecke and Segeln sections need route-/sailing-specific content the BSO
# articles don't supply, so no theme maps to them — those blocks stay unfilled
# until seeded from a dedicated source.
_BODENSEE_BLOCK_BY_THEME: dict[str, str] = {
    "definitionen": "bodensee_allgemeines",
    "recht_dokumente": "bodensee_allgemeines",
    "lichter_signale": "bodensee_signale",
    "schifffahrtszeichen": "bodensee_zeichen",
    "verkehrsregeln": "bodensee_fahrregeln",
    "seemannschaft": "bodensee_umwelt_seemannschaft",
    "umweltschutz": "bodensee_umwelt_seemannschaft",
    "wetterkunde": "bodensee_wetter_navigation",
    "navigation": "bodensee_wetter_navigation",
    "gezeiten": "bodensee_wetter_navigation",
}


def bodensee_block_for(theme: str) -> str:
    """Exam-block id for a BSO-seeded prose question of the given theme ('' when
    the theme has no Bodensee section yet)."""
    return _BODENSEE_BLOCK_BY_THEME.get(theme, "")

# A definitions article announces itself structurally — title "Begriffe(n)…" /
# "Begriffsbestimmungen", or the text opening "Im Sinne dieser Verordnung …".
# Detected before keyword rules so a term list enumerating buoys/lights isn't
# mis-tagged as signalisation.
_DEF_TITLE = re.compile(r"\bbegriffs?(bestimmungen|erkl(ä|ae)rungen)?\b", re.I)
_DEF_TEXT_START = re.compile(
    r"^\s*(im sinne (dieser|der) (verordnung|ordnung|regeln)|"
    r"in diesen regeln (haben|bedeuten)|bedeuten in diesen regeln)", re.I)


def _is_definitions(title: str, text: str) -> bool:
    return bool(_DEF_TITLE.search(title or "")) or \
        bool(_DEF_TEXT_START.match((text or "").lstrip()))


# Ordered, evaluated first-match-wins. High precision deliberately beats recall;
# whatever no rule catches falls back to the source default (set per ordinance).
_RULES: list[tuple[str, re.Pattern[str]]] = [
    # Lights / shapes / sound signals — checked before the traffic rules because
    # the lights articles also describe courses and give-way situations.
    ("lichter_signale", re.compile(
        r"\b(lichterf(ü|ue)hrung|lichter|positionslamp|toplicht|hecklicht|"
        r"seitenlicht|ankerlicht|funkellicht|sichtzeichen|signalk(ö|oe)rper|"
        r"schallsignal|nebelsignal|schallzeichen|glocke|pfeife|nebelhorn|"
        r"flagge|flaggensignal|ball|kegel|zylinder)\b", re.I)),
    # Buoyage / marks / fairway signs (IALA Region A).
    ("schifffahrtszeichen", re.compile(
        r"\b(schifffahrtszeichen|seezeichen|betonnung|fahrwasser(tonne|seite)?|"
        r"tonne[n]?|spierentonne|leuchttonne|bake[n]?|kardinal|lateralzeichen|"
        r"lateralsystem|steuerbordtonne|backbordtonne|tafelzeichen|"
        r"hinweiszeichen|verbotszeichen|gebotszeichen)\b", re.I)),
    # Tides & current (coastal: See/SKS).
    ("gezeiten", re.compile(
        r"\b(gezeiten|tide[nh]?|ebbe|flut|tidenhub|hochwasser|niedrigwasser|"
        r"tidenstrom|gezeitenstrom)\b", re.I)),
    # Weather.
    ("wetterkunde", re.compile(
        r"\b(wetter|wetterkunde|windst(ä|ae)rke|beaufort|sturmwarnung|starkwind|"
        r"b(ö|oe)en|seegang|hochdruck|tiefdruck|(kalt|warm)front|gewitter)\b", re.I)),
    # Environmental protection.
    ("umweltschutz", re.compile(
        r"\b(umweltschutz|gew(ä|ae)sserschutz|naturschutz|abf(ä|ae)ll|"
        r"(ö|oe)l(unfall|verschmutzung)?|einleit|schutzgebiet|vogelschutz|"
        r"abwasser)\b", re.I)),
    # Navigation / chart work (coastal: See/SKS).
    ("navigation", re.compile(
        r"\b(navigation|seekarte|kartenkurs|peilung|kompasskurs|missweisung|"
        r"deviation|besteckrechnung|seemeile|leuchtfeuer|leuchtturm|"
        r"feuerkennung)\b", re.I)),
    # Seamanship: knots, mooring, anchoring, manoeuvres, safety, engine.
    ("seemannschaft", re.compile(
        r"\b(seemannschaft|knoten|leine[n]?|festmach|ankern|anker|man(ö|oe)ver|"
        r"mann (ü|ue)ber bord|rettungs(weste|insel|mittel)|kentern|schleuse|"
        r"fender|kraftstoff|brandbek(ä|ae)mpfung|l(ö|oe)schmittel)\b", re.I)),
    # Traffic rules / right of way — broad, so it runs late.
    ("verkehrsregeln", re.compile(
        r"\b(vorfahrt|ausweich(regel|pflicht|en)?|wegerecht|begegn|(ü|ue)berhol|"
        r"vorbeifahr|kurs halten|fahrregeln|fahrverbot|geschwindigkeit|"
        r"sperrgebiet|sperrung|kreuzen|recht voraus)\b", re.I)),
    # Law, licensing, documents, alcohol limits.
    ("recht_dokumente", re.compile(
        r"\b(sportbootf(ü|ue)hrerschein|f(ü|ue)hrerschein|fahrerlaubnis|"
        r"zulassung|kennzeichen|versicherung|geltungsbereich|ordnungswidrigkeit|"
        r"bu(ß|ss)geld|promille|alkohol|vorschrift|erlaubnis|ausweis)\b", re.I)),
]


def tag_theme(ref: str = "", title: str = "", text: str = "",
              default: str | None = None) -> str:
    """Return the best German theme id for a unit. ``default`` (the ordinance's
    source-level hint) is the fallback and wins when no keyword rule fires."""
    if _is_definitions(title, text):
        return "definitionen"
    haystack = " ".join((ref, title, text)).lower()
    for theme_id, pattern in _RULES:
        if pattern.search(haystack):
            return theme_id
    if default and default in THEMES:
        return default
    # Law text with no stronger signal is procedural / legal.
    return "recht_dokumente"


def is_valid(theme_id: str) -> bool:
    return theme_id in THEMES
