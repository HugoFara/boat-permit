"""Question scope — which harmonised base governs a question, and whose overlay.

Navigation content composes by **lex specialis** (see :mod:`src.jurisdictions`):
the narrowest applicable regime wins, and what it doesn't override is inherited
from a larger set. This module places each :class:`Question` at one rung of that
hierarchy:

  * ``universal`` — seamanship portable on any water under any code: knots, general
                    weather, engine, first aid, environment. The largest set.
  * ``cevni``     — the harmonised **inland** traffic code: signs, buoyage, lights,
                    sound signals, inland right-of-way. Portable across CEVNI states.
  * ``colregs``   — the harmonised **maritime** traffic code (RIPAM/KVR): sea
                    signage and collision rules. Portable across the sea.
  * ``national``  — country statute: permits, registration, insurance, sanctions,
                    bilateral frontier waters. Belongs to one country.
  * ``local``     — tied to one water body: a named local wind, a lake's storm
                    signals, or an *excluded* regime (Lake Constance / BSO).

``universal``/``cevni``/``colregs`` are the **bases** (the portable, shareable
core); ``national``/``local`` are the **overlays**. The harmonised core of a permit
is ``universal`` plus its track's base — CEVNI for an inland permit, COLREGS for a
sea permit.

The classification is **derived, never stored** — computed at export time from the
question's theme + ref/source/stem, so the schema and the per-language national
bundles stay byte-identical. It is a deliberately auditable heuristic (every rule
names itself) and a *starting point*: a country-agent tunes the keyword sets below
for its own law (its statute → ``national``, its local waters → ``local``, its sea
content → ``colregs``).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from . import jurisdictions

if TYPE_CHECKING:                      # avoid any import cycle; we only duck-type
    from .questions.schema import Question

# The portable bases (the shareable core) and the country/water overlays.
BASES = ("universal", "cevni", "colregs")
OVERLAYS = ("national", "local")
SCOPES = set(BASES) | set(OVERLAYS)
DEFAULT_SCOPE = "universal"            # lex generalis: the safe, largest set

# Within `lois`: country *statute* (permits, registration, insurance, sanctions)
# rather than the portable navigation rules. Country-specific → national.
_NATIONAL_ADMIN = re.compile(
    r"\b(permis|autoris\w*|immatricul\w*|assuranc\w*|attestation|certificat|"
    r"plaque|taxe|redevance|registre|examen|sanction|amende|retrait|"
    r"responsabilit\w*|ofrou|ocv|office cantonal)\b", re.I)

# Within `meteorologie`: tied to a specific lake (named local winds, or a lake's
# storm-warning signal operation) → local. Generic weather is universal.
_LOCAL_METEO = re.compile(
    r"\b(l[eé]man|bise|joran|vaudaire|bornan|s[eé]chard|morget|rebat|molan|"
    r"s[uû]dois|vauderon|avis de (fort )?vent|avis de temp[eê]te|"
    r"feux d.alerte|scintillant)\b", re.I)

# Bilateral / frontier wording that pins a question to a specific country pairing
# → national.
_FRONTIER = re.compile(r"\b(franco-suisse|eaux fronta|convention.*france|"
                       r"accord.*france)\b", re.I)

# Maritime markers: when a traffic-code question carries them, it is governed by
# COLREGS rather than CEVNI (sea buoyage/lights/rules differ from inland). Tuned
# conservatively to avoid catching inland lakes; extend per a country's sea bank.
_MARITIME = re.compile(
    r"(\ben mer\b|abordage en mer|\bripam\b|colreg|\bkvr\b|"
    r"seeschifffahrt\w*|seeschifffahrtsstra\w*|seekarte\w*|seezeichen\w*|"
    r"hochsee\w*|k[üu]ste\w*|sbf[- ]?see|navigation maritime|"
    r"feu\w* de mer|mille\w* nautique|c[oô]ti[eè]r\w*|\bmaritime\b)", re.I)


def _haystack(q: "Question") -> str:
    p = q.provenance
    return " ".join((q.stem or "", getattr(p, "ref", "") or "",
                     getattr(p, "source", "") or "")).lower()


def classify(q: "Question") -> str:
    """Return the scope of a question — one of :data:`SCOPES`. Rules run narrowest
    first (lex specialis): an excluded water, then a named-local water, then
    national statute, then the harmonised base (maritime → ``colregs``, inland
    traffic → ``cevni``), and finally portable seamanship (``universal``)."""
    text = _haystack(q)
    theme = q.theme

    # 1. A water that REPLACES the base with its own code (Bodensee/BSO): its
    #    signage is never portable, whatever the theme. "Which waters are excluded"
    #    is a jurisdiction fact (src.jurisdictions).
    if jurisdictions.excluded_regime(text):
        return "local"

    # 2. Named-local water specifics (a lake's winds / its storm-signal operation).
    if theme == "meteorologie" and _LOCAL_METEO.search(text):
        return "local"

    # 3. National overlay: bilateral frontier waters, or country statute.
    if theme == "eaux_frontalieres" or _FRONTIER.search(text):
        return "national"
    if theme == "lois" and _NATIONAL_ADMIN.search(text):
        return "national"

    # 4. Harmonised traffic code — inland (CEVNI) vs maritime (COLREGS). Signs and
    #    the navigation rules in `lois` are traffic-code content.
    if theme in ("signalisation", "lois"):
        return "colregs" if _MARITIME.search(text) else "cevni"

    # 5. Universal seamanship: matelotage, definitions, voile, generic weather —
    #    portable on any water under any code.
    return "universal"


def scope_counts(questions: list["Question"]) -> dict[str, int]:
    """How many questions fall in each scope (for build summaries / audits)."""
    counts = {s: 0 for s in SCOPES}
    for q in questions:
        counts[classify(q)] += 1
    return counts


def ids_by_base(questions: list["Question"]) -> dict[str, set]:
    """The question ids of each portable base (``universal``/``cevni``/``colregs``).
    Overlay-scoped questions (national/local) are not part of any shareable core."""
    out: dict[str, set] = {b: set() for b in BASES}
    for q in questions:
        s = classify(q)
        if s in out:
            out[s].add(q.id)
    return out


def bases_present(questions: list["Question"]) -> list[str]:
    """The bases that actually have content, in :data:`BASES` order."""
    ids = ids_by_base(questions)
    return [b for b in BASES if ids[b]]


def core_bank(questions: list["Question"]) -> list["Question"]:
    """The shareable core: every base-scoped question (``universal`` ∪ ``cevni`` ∪
    ``colregs``) — the cross-country/cross-track reusable subset."""
    return [q for q in questions if classify(q) in BASES]
