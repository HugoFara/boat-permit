"""The 6 official exam themes and the rules for tagging knowledge units to them.

The taxonomy is the normalization target: every knowledge unit ends up tagged to
exactly one theme so Phase 2 can balance question selection the way the real exam
does. Tagging is deliberately simple and auditable (source defaults + keyword
heuristics over the unit's ref/title/text) — never a black box.
"""

from __future__ import annotations

import re
import unicodedata

# Canonical theme ids (stable keys) -> human label (French, as on the exam).
THEMES: dict[str, str] = {
    "definitions": "Définitions",
    "meteorologie": "Météorologie",
    "lois": "Lois sur la navigation en eaux intérieures",
    "signalisation": "Signalisation et signaux acoustiques",
    "matelotage": "Matelotage",
    "eaux_frontalieres": "Eaux frontalières",
}

# Keyword heuristics, evaluated in priority order. The first theme whose pattern
# matches the unit's searchable text wins, unless the unit carries an explicit
# theme already (e.g. a prose source pinned by its parser).
# A terminology article announces itself *structurally*, and we detect it before
# the keyword rules so it isn't stolen by the generic signalisation match (a
# definitions list naturally enumerates signal/buoy/light terms). Two anchored
# signals, both high-precision:
#  - the *title* ends in "Définition(s)" or is "Signification de quelques termes"
#    (ONI art. 2, RNL art. 1, ONI art. 61/142);
#  - the *text* opens with the canonical definitional lead-in.
# Anchoring matters: it keeps genuine signalisation articles that merely *contain*
# an inline definition (e.g. RNL art. 46 "on entend par: un son bref…") out.
_DEF_TITLE = re.compile(
    r"(^\s*d[eé]finitions?\b|d[eé]finitions?\s*$|"
    r"signification de (quelques )?termes\s*$)", re.I)
_DEF_TEXT_START = re.compile(
    r"^\s*(\d+\s*)?(dans (la pr[eé]sente (ordonnance|convention)|"
    r"le pr[eé]sent r[eè]glement)\s*:|au sens de la pr[eé]sente)", re.I)


def _is_definitions(title: str, text: str) -> bool:
    return bool(_DEF_TITLE.search(title or "")) or \
        bool(_DEF_TEXT_START.match((text or "").lstrip()))


_RULES: list[tuple[str, re.Pattern[str]]] = [
    # Storm-warning signals are a Météorologie exam topic, not Signalisation —
    # this narrow rule runs first so "avis de tempête / fort vent / feux d'alerte"
    # wins over the generic signal/feux match below. Buoy & light signs (which
    # never use this wording) stay in Signalisation.
    ("meteorologie", re.compile(
        r"(avis de (fort )?vent|avis de temp[eê]te|signaux d.avis|"
        r"signaux de temp[eê]te|feux d.alerte|signaux de fort vent)")),
    ("signalisation", re.compile(
        r"\b(signal|signalisation|signaux|balis|bou[eé]e|feu[x]?|pavillon|"
        r"acoustique|sonore|marque|panneau)\b")),
    # Note: bare "vent" is deliberately NOT a keyword — it false-matches
    # "bateaux à voile" right-of-way rules and "surface vélique". Real météo is
    # caught by the storm rule above, the named winds here, and source defaults
    # (the MétéoSuisse "Le Vent" sections fall back to their meteorologie default).
    ("meteorologie", re.compile(
        r"\b(m[eé]t[eé]o|bise|joran|vaudaire|bornan|s[eé]chard|temp[eê]te|"
        r"orage|rafale|nu[ae]ge|grain)\b")),
    ("matelotage", re.compile(
        r"\b(matelotage|n[oœ]ud|amarr|mouillage|ancre|cordage|bitte|taquet|"
        r"demi-cl[eé]|chaise)\b")),
    ("eaux_frontalieres", re.compile(
        r"\b(l[eé]man|fronti[eè]re|franco-suisse|france|eaux fronta)\b")),
    # Note: there is no loose "definitions" keyword rule. A bare "définition" /
    # "au sens de la présente" / "on entend par" fires inside procedural articles
    # that merely *cite* a definition (e.g. ONI art. 84/91b on permits). Real
    # terminology articles are caught up-front by the anchored _is_definitions().
]


def _norm(text: str) -> str:
    """Lowercase; keep accents (rules match accented or not via [eé] classes)."""
    return (text or "").lower()


def tag_theme(ref: str = "", title: str = "", text: str = "",
              default: str | None = None) -> str:
    """Return the best theme id for a unit. `default` (a source-level hint) is
    used as a fallback and also wins ties when no keyword rule fires."""
    # High-precision structural check first: a genuine terminology article goes to
    # Définitions even though its term list mentions signals, buoys, lights, etc.
    if _is_definitions(title, text):
        return "definitions"
    haystack = _norm(" ".join((ref, title, text)))
    for theme_id, pattern in _RULES:
        if pattern.search(haystack):
            return theme_id
    if default and default in THEMES:
        return default
    # Sensible last resort: law text with no stronger signal is "lois".
    return "lois"


def is_valid(theme_id: str) -> bool:
    return theme_id in THEMES
