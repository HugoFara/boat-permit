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
_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("signalisation", re.compile(
        r"\b(signal|signalisation|signaux|balis|bou[eé]e|feu[x]?|pavillon|"
        r"acoustique|sonore|marque|panneau)\b")),
    ("meteorologie", re.compile(
        r"\b(m[eé]t[eé]o|vent|bise|joran|vaudaire|bornan|s[eé]chard|temp[eê]te|"
        r"orage|avis de (fort )?vent|rafale|nu[ae]ge)\b")),
    ("matelotage", re.compile(
        r"\b(matelotage|n[oœ]ud|amarr|mouillage|ancre|cordage|bitte|taquet|"
        r"demi-cl[eé]|chaise)\b")),
    ("eaux_frontalieres", re.compile(
        r"\b(l[eé]man|fronti[eè]re|franco-suisse|france|eaux fronta)\b")),
    ("definitions", re.compile(
        r"\b(d[eé]finition|on entend par|au sens de la pr[eé]sente|terminologie)\b")),
]


def _norm(text: str) -> str:
    """Lowercase; keep accents (rules match accented or not via [eé] classes)."""
    return (text or "").lower()


def tag_theme(ref: str = "", title: str = "", text: str = "",
              default: str | None = None) -> str:
    """Return the best theme id for a unit. `default` (a source-level hint) is
    used as a fallback and also wins ties when no keyword rule fires."""
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
