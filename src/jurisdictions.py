"""Jurisdictions — the regime tree that orders navigation law by *applicability*.

National boating rules compose by **lex specialis derogat legi generali**: the more
specific regime overrides the more general one, and everything it does *not*
override is inherited from the broader set. So the regimes form a single tree, each
node a **precision under a larger set** (its parent, recorded in ``refines``):

    UNIVERSAL                         seamanship valid on any water, any country
    ├─ CEVNI                          inland traffic code (signs/lights/sounds/rules)
    │  ├─ CH-INLAND  (implements)     ONI/RNL — Switzerland's enactment
    │  ├─ DE-INLAND  (implements)     BinSchStrO
    │  ├─ FR-INLAND  (implements)     RGP / eaux intérieures
    │  ├─ RHINE      (diverges)       CCNR / RheinSchPV — own police regs
    │  ├─ LEMAN      (diverges)       Franco-Swiss règlement de la navigation
    │  └─ BODENSEE   (excluded)       BSO — its *own* code, signage NOT portable
    └─ COLREGS                        maritime traffic code (the sea base)
       ├─ DE-MARITIME (implements)    SeeSchStrO / KVR — SBF See, SKS, SSS, SHS
       └─ FR-MARITIME (implements)    RIPAM — option côtière

The **base ancestor** a node reaches (UNIVERSAL / CEVNI / COLREGS) is its
portability class; :mod:`src.scope` reads exactly that to bucket questions. The
**relation** to that base says how the node sits under it: ``implements`` (national
enactment), ``diverges`` (mostly the base, documented deviations), ``excluded`` (a
named water that replaces the base with its own code — only this one keeps signage
out of the shared core), or ``is_base`` (the base itself).

It is **derived, not duplicated**: each country contributes one regime node *per
track* (inland / maritime), read from the live :mod:`src.countries` registry
(``derives_from``) — adding a country adds its regimes automatically. Only the
supra-national bases and the shared-water regimes are declared here by hand.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from . import countries

# What kind of node this is in the regime tree.
KINDS = {"base", "national", "shared_water"}

# A node's relation to its base ancestor — the portability fact src.scope reads.
#   is_base    — the harmonised code itself (UNIVERSAL / CEVNI / COLREGS).
#   implements — a national enactment of the base; its harmonised content IS core.
#   diverges   — mostly the base, with its own documented deviations (Rhine, Léman).
#   excluded   — a named water with its OWN code (Bodensee/BSO); signage NOT portable.
RELATIONS = {"is_base", "implements", "diverges", "excluded"}

# The navigation track a regime governs (which base it refines).
TRACKS = {"inland", "maritime"}

# The default jurisdiction: the root of the portability tree. The project default
# country is INT (the harmonised layer), which is a *base* and contributes no
# national node, so the sensible default is the universal root itself.
DEFAULT = "UNIVERSAL"


@dataclass(frozen=True)
class Jurisdiction:
    code: str                       # UNIVERSAL/CEVNI/COLREGS, CH-INLAND…, BODENSEE…
    name: str
    kind: str                       # one of KINDS
    refines: str = ""               # parent code (the larger set); "" only at the root
    relation: str = "implements"    # one of RELATIONS
    track: str = ""                 # one of TRACKS, or "" for UNIVERSAL
    members: tuple[str, ...] = ()    # for shared_water: the sharing countries
    derives_from: str = ""          # the src.countries code this draws display data from
    note: str = ""


# --- track inference ----------------------------------------------------------
# A permit declares its track (`Permit.track`); when it doesn't, infer it from the
# permit code/label. "Binnen/intérieur/fluvial" pins inland even past a stray
# "See"; otherwise maritime markers (See, côtière, Küste, SKS/SSS/SHS…) → maritime.
_INLAND_PERMIT = re.compile(r"\b(binnen|int[eé]rieur\w*|inland|fluvial\w*)\b", re.I)
_MARITIME_PERMIT = re.compile(
    r"(\bsee\b|seeschiffer|hochsee|k[üu]ste|sks|sss|shs|sbf[- ]?see|"
    r"c[oô]ti[eè]re|maritime|offshore|\bmer\b)", re.I)


def permit_track(permit) -> str:
    """The track a permit grants: ``inland`` | ``maritime``. Honours an explicit
    ``Permit.track`` and otherwise infers from its code/label."""
    explicit = getattr(permit, "track", "") or ""
    if explicit in TRACKS:
        return explicit
    blob = f"{getattr(permit, 'code', '')} {getattr(permit, 'label', '')}"
    if _INLAND_PERMIT.search(blob):
        return "inland"
    return "maritime" if _MARITIME_PERMIT.search(blob) else "inland"


_BASE_FOR_TRACK = {"inland": "CEVNI", "maritime": "COLREGS"}


def _build() -> dict[str, Jurisdiction]:
    reg: dict[str, Jurisdiction] = {}

    # 1. The harmonised bases — the roots of the portability tree.
    reg["UNIVERSAL"] = Jurisdiction(
        code="UNIVERSAL", name="Universal seamanship", kind="base",
        relation="is_base",
        note="Portable boat-handling that holds under any code: weather, knots, "
             "engine, first aid, environment. The largest set.")
    reg["CEVNI"] = Jurisdiction(
        code="CEVNI", name="CEVNI — European inland-navigation code", kind="base",
        refines="UNIVERSAL", relation="is_base", track="inland",
        note="UNECE harmonised inland traffic code; the shared inland core.")
    reg["COLREGS"] = Jurisdiction(
        code="COLREGS", name="COLREGS — international rules at sea", kind="base",
        refines="UNIVERSAL", relation="is_base", track="maritime",
        note="IMO maritime collision regs (RIPAM/KVR/RIPAM); the shared sea core.")

    # 2. Country regimes, derived from the operational registry — one node per
    #    track the country's permits cover (inland and/or maritime). A
    #    sourcing-only member (no permits — the supra-national INT layer that
    #    grounds the bases themselves) is NOT a national implementer, so it
    #    contributes no national node.
    for code in countries.codes():
        c = countries.get(code)
        if not c.permits:
            continue
        tracks = sorted({permit_track(p) for p in c.permits.values()},
                        key=lambda t: t != "inland")
        for track in tracks:
            jcode = f"{c.code}-{track.upper()}"
            reg[jcode] = Jurisdiction(
                code=jcode, name=f"{c.name} — {track}", kind="national",
                refines=_BASE_FOR_TRACK[track], relation="implements",
                track=track, derives_from=c.code)

    # 3. Shared / special waters — declared by hand (a Country cannot model them).
    #    Bodensee is the only *excluded* regime: it replaces CEVNI with the BSO, so
    #    its signage is not portable. The Rhine and the Léman merely *diverge*
    #    (own police regs over a CEVNI base) and stay in the core.
    reg["BODENSEE"] = Jurisdiction(
        code="BODENSEE", name="Lac de Constance / Bodensee", kind="shared_water",
        refines="CEVNI", relation="excluded", track="inland",
        members=("CH", "DE", "AT"),
        note="Bodensee-Schifffahrts-Ordnung (BSO); outside CEVNI — its signage is "
             "not portable into the European core.")
    reg["RHINE"] = Jurisdiction(
        code="RHINE", name="Rhin / Rhein (CCNR)", kind="shared_water",
        refines="CEVNI", relation="diverges", track="inland",
        members=("CH", "FR", "DE", "NL"),
        note="Rheinschifffahrtspolizeiverordnung (RheinSchPV), Central Commission "
             "for the Navigation of the Rhine — CEVNI-aligned with own deviations.")
    reg["LEMAN"] = Jurisdiction(
        code="LEMAN", name="Lac Léman (franco-suisse)", kind="shared_water",
        refines="CEVNI", relation="diverges", track="inland", members=("CH", "FR"),
        note="Règlement de la navigation sur le Léman — bilateral CH/FR regime over "
             "a CEVNI base; named local winds (bise, joran…).")
    return reg


REGISTRY: dict[str, Jurisdiction] = _build()


def get(code: str | None) -> Jurisdiction:
    """The Jurisdiction for a code (case-insensitive); defaults when empty, raises
    on an unknown non-empty code."""
    if not code:
        return REGISTRY[DEFAULT]
    key = code.upper()
    if key not in REGISTRY:
        raise ValueError(f"unknown jurisdiction {code!r}; choose from {sorted(REGISTRY)}")
    return REGISTRY[key]


def _kind(code: str) -> str:
    return REGISTRY[code].kind


def codes() -> list[str]:
    """All codes in tree order: the bases (root first), then country regimes
    (by country code, inland before maritime), then shared waters."""
    bases = [c for c in REGISTRY if _kind(c) == "base"]
    bases.sort(key=lambda c: (REGISTRY[c].refines != "", c != "CEVNI", c))
    nat = [c for c in REGISTRY if _kind(c) == "national"]
    nat.sort(key=lambda c: (REGISTRY[c].derives_from, REGISTRY[c].track != "inland"))
    waters = sorted(c for c in REGISTRY if _kind(c) == "shared_water")
    return bases + nat + waters


def relation(code: str) -> str:
    """How a jurisdiction sits under its base (its portability fact)."""
    return get(code).relation


def track(code: str) -> str:
    """The navigation track a jurisdiction governs (inland/maritime, or "")."""
    return get(code).track


def ancestors(code: str) -> list[str]:
    """The chain of broader regimes above ``code``, nearest parent first up to the
    root — the larger sets this one is a precision of."""
    chain: list[str] = []
    cur = get(code).refines
    while cur:
        chain.append(cur)
        cur = REGISTRY[cur].refines
    return chain


def base_of(code: str) -> str:
    """The portability base a jurisdiction belongs to: itself if it is a base, else
    the nearest base ancestor (CEVNI / COLREGS / UNIVERSAL)."""
    j = get(code)
    if j.kind == "base":
        return j.code
    for anc in ancestors(j.code):
        if REGISTRY[anc].kind == "base":
            return anc
    return "UNIVERSAL"


# --- the excluded-regime guard ------------------------------------------------
# Wording that ties a question to a CEVNI-*excluded* water (its signage replaced by
# an own code, so never portable). Derived from the registry: a marker is needed
# per excluded node because matching prose can't come from the dataclass. Today
# only Lake Constance qualifies; add a marker when another excluded regime appears.
_EXCLUDED_MARKERS: dict[str, re.Pattern[str]] = {
    "BODENSEE": re.compile(
        r"\b(bodensee|bso|bodensee-schifffahrts|lac de constance|"
        r"lago di costanza)\b", re.I),
}
# Invariant: only regimes whose relation is "excluded" carry a marker.
assert {c for c in _EXCLUDED_MARKERS if REGISTRY[c].relation == "excluded"} \
    == set(_EXCLUDED_MARKERS), "excluded-regime markers must match relation='excluded'"


def excluded_codes() -> list[str]:
    """Jurisdiction codes whose base is *replaced* by an own code (relation
    ``excluded``) — their signage must never enter the shared core."""
    return [c for c in codes() if REGISTRY[c].relation == "excluded"]


def excluded_regime(text: str) -> str | None:
    """If ``text`` (a question's ref/source/stem) ties it to a CEVNI-excluded
    regime, return that code (e.g. 'BODENSEE'); else None. Used by :mod:`src.scope`
    to keep non-portable signage out of the harmonised core."""
    for code, pat in _EXCLUDED_MARKERS.items():
        if pat.search(text or ""):
            return code
    return None


def as_manifest() -> list[dict]:
    """The descriptive table for a player/regime picker, in :func:`codes` order."""
    return [{
        "code": j.code, "name": j.name, "kind": j.kind, "refines": j.refines,
        "relation": j.relation, "track": j.track, "base": base_of(j.code),
        "members": list(j.members), "derives_from": j.derives_from, "note": j.note,
    } for j in (REGISTRY[c] for c in codes())]
