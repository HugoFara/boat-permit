"""Principle tagging — the join key between a question and its "why" concept.

Roadmap group A/D1: a *principle* is the generative rule a question tests (IALA
buoyage logic, the navigation-light grammar, the give-way hierarchy). One concept
card explains a principle; every question carrying that ``principle`` tag links to
it. Tags are derived **deterministically** here at build time, so re-running the
build yields identical tags (no model, no randomness).

Scope (decided from the data): the pilot tags the two buckets that dominate the
corpus and are genuinely *reconstructable* — signals (~416 q) and give-way rules
(~251 q). Everything else stays untagged ("") and the player simply shows no card,
so the feature degrades gracefully and never mislabels.

The classifier is conservative: it matches language-specific keywords against the
stem + choice text + explanation and assigns the first principle whose keyword
set hits. A small set of *unambiguous* themes (e.g. balisage → iala-buoyage) act
as a fallback when no keyword matched. When nothing is confident, it returns "".
"""

from __future__ import annotations

import sqlite3
import unicodedata

# --- the principle taxonomy (stable, language-neutral slugs) -------------------
# Each entry: slug -> human gloss. The slug is what lands in Question.principle
# and keys the concept bank; the gloss is documentation only.
PRINCIPLES: dict[str, str] = {
    # signals family
    "iala-buoyage":   "Lateral & cardinal marks: the IALA buoyage system",
    "nav-lights":     "Navigation lights: who shows what, and why",
    "day-shapes":     "Day shapes (ball / cone / cylinder)",
    "sound-signals":  "Sound-signal grammar (short / long blasts)",
    "waterway-signs": "Inland-waterway signboards (CEVNI / RGP / SchifffahrtsZ.)",
    # give-way family
    "give-way":       "The give-way hierarchy and steering & sailing rules",
}

# Keyword tables, checked in this priority order (most specific signal types
# first, so a light-and-sound question is tagged by its dominant cue). Matching
# is accent-insensitive substring on the normalised text. Keep keywords
# discriminating — a false hit mislabels a question, so prefer precision.
_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("sound-signals", (
        "signal sonore", "son bref", "sons bref", "son prolonge", "sons prolonge",
        "coups", "sifflet",
        "sound signal", "short blast", "long blast", "prolonged blast", "whistle",
        "schallsignal", "kurzer ton", "langer ton", "pfeife", "glocke",
        # declined German forms the nominative keys miss: "Dauer eines kurzen Tons",
        # "vier kurze/kurzen Töne(n)" — the catalogue asks blast questions in the
        # genitive/plural, where "kurzer ton" never substring-matches.
        "kurzen ton", "langen ton", "kurze tone", "lange tone",
        "segnale sonoro", "suono breve", "suono prolungato", "fischio",
    )),
    ("day-shapes", (
        "marque de jour", "ballon", "cone", "cylindre", "boule noire",
        "day shape", "day-shape", "black ball", "black cone", "cylinder",
        "signalkorper", "schwarzer ball", "kegel", "zylinder", "rhombus",
        "segnale diurno", "cono", "pallone", "cilindro",
    )),
    ("nav-lights", (
        "feu de", "feux de", "feu blanc", "feu rouge", "feu vert", "tricolore",
        "feu de tete de mat", "feu de cote", "feu de poupe", "feu visible sur",
        "navigation light", "masthead light", "sidelight", "sternlight",
        "all-round light", "all round light", "stern light",
        "topplicht", "seitenlicht", "hecklicht", "rundumlicht", "lichterfuhrung",
        # generic German light-configuration phrasing the part-specific keys miss:
        # "Was bedeuten diese Lichter", "Welches Fahrzeug führt diese Lichter",
        # "zwei blaue Lichter übereinander". Discriminating — these are light-signal
        # questions, not sound/shape (which run first in this table anyway).
        "diese lichter", "blaue lichter", "lichter ubereinander",
        "lichter fuhren", "lichter gefuhrt", "lichter zeigen", "lichter gezeigt",
        "fanale", "luce di", "luci di", "luce bianca",
    )),
    ("iala-buoyage", (
        "bouee", "balise", "laterale", "cardinale", "espar", "voyant",
        "eaux saines", "danger isole", "marque speciale",
        "buoy", "lateral mark", "cardinal mark", "safe water", "isolated danger",
        "special mark", "port-hand", "starboard-hand", "preferred channel",
        "spierentonne", "seitenzeichen", "kardinalzeichen",
        # NB: bare babord/tribord/backbord/steuerbord/"tonne" are intentionally
        # NOT keywords — port/starboard appear in give-way & steering questions too,
        # so they over-matched. Buoyage is caught by the mark-specific terms above.
        "boa", "gavitello", "laterale", "cardinale", "acque sicure",
    )),
    ("waterway-signs", (
        "panneau", "signalisation fluviale", "tableau d'eau", "ecriteau",
        "signal de la voie", "panneau d'interdiction", "panneau d'obligation",
        "signboard", "waterway sign", "shore mark", "notice mark",
        "tafelzeichen", "verbotszeichen", "gebotszeichen", "hinweiszeichen",
        "schifffahrtszeichen",
        "segnaletica", "pannello", "cartello",
    )),
    ("give-way", (
        "priorite", "route libre", "privilegie", "donner la route", "s'ecarter",
        "route de collision", "croisement", "depassement", "face a face",
        "navire qui doit manoeuvrer", "give way", "give-way", "stand-on",
        "stand on", "overtaking", "crossing situation", "head-on", "right of way",
        "vorfahrt", "ausweichen", "kurs halten", "kurshalter",
        "ausweichpflichtig", "uberholen", "kreuzen", "entgegenkommend",
        "vorfahrtsregel", "precedenza", "dare la rotta", "sorpasso", "incrocio",
        "rotta di collisione",
    )),
]

# Fallback: a theme that is itself unambiguous about its principle. Only used
# when no keyword matched, so it never overrides a confident keyword hit.
_THEME_DEFAULT: dict[str, str] = {
    "balisage":              "iala-buoyage",
    "feux_signaux":          "nav-lights",
    "signalisation_fluviale": "waterway-signs",
    "lights_shapes":         "nav-lights",
    "sound_light_signals":   "sound-signals",
    "steering_sailing":      "give-way",
    "regles_route":          "give-way",
}


def _norm(s: str) -> str:
    """Lower-case, strip accents — so 'priorité' and 'priorite' match alike."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower()


def tag_for(stem: str, choices_text: str = "", explanation: str = "",
            theme: str = "") -> str:
    """Return the principle slug for one question's text, or "" if not confident.

    Keyword match (priority order) wins; an unambiguous theme is the fallback.
    """
    hay = _norm(" ".join([stem, choices_text, explanation]))
    for slug, kws in _KEYWORDS:
        if any(kw in hay for kw in kws):
            return slug
    return _THEME_DEFAULT.get(theme, "")


def tag_questions(conn: sqlite3.Connection, overwrite: bool = False) -> dict:
    """Tag every question in a bank in place, writing Question.principle.

    Idempotent and deterministic. By default it only fills *empty* principles
    (so a hand-curated tag is never clobbered); ``overwrite=True`` retags all.
    Returns a stats dict: total, tagged, and a per-principle breakdown.
    """
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, stem, explanation, theme, principle FROM questions"
    ).fetchall()
    by_principle: dict[str, int] = {}
    tagged = 0
    cur = conn.cursor()
    for r in rows:
        if r["principle"] and not overwrite:
            by_principle[r["principle"]] = by_principle.get(r["principle"], 0) + 1
            continue
        ctext = " ".join(
            c[0] or "" for c in conn.execute(
                "SELECT text FROM choices WHERE question_id=?", (r["id"],))
        )
        slug = tag_for(r["stem"], ctext, r["explanation"] or "", r["theme"])
        if slug:
            cur.execute("UPDATE questions SET principle=? WHERE id=?", (slug, r["id"]))
            tagged += 1
            by_principle[slug] = by_principle.get(slug, 0) + 1
    conn.commit()
    conn.row_factory = None
    return {"total": len(rows), "tagged": tagged,
            "by_principle": dict(sorted(by_principle.items()))}
