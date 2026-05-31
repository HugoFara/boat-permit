"""Stage 3 — validate the *derived* common core against an official catalogue.

The German ELWIS bank is the project's one ground-truth-valid bank: it *is* the
amtliche Fragenkatalog. The CH and FR banks are *derived* from law, of unmeasured
fidelity. Because :mod:`src.scope` tags every question by harmonised base
(``universal``/``cevni``/``colregs``), the official German questions on a shared
base can act as a yardstick for the derived ones on the *same* base — the only
non-circular cross-check available (one side is official; the classifier restricts
the comparison to genuinely shared scope).

Two instruments, deliberately different in cost and confidence:

  * :func:`coverage` — deterministic, ``$0``, CI-friendly. Reports, per harmonised
    base, (1) an **instrumentation rate** — what fraction of the official bank any
    instrument can even see, so no figure is read as covering more than it measures;
    (2) a **bounded coverage figure** on that instrumented slice, via the shared
    ``principle`` tag, weighted by how often the official bank tests each topic; and
    (3) a fine-grained, hand-curated **concept probe** (precise but low-reach) that
    spot-checks individual harmonised concepts. It answers "how much of what the
    official bank tests — and that I can actually measure — does my derived bank
    carry?", never "is an answer right". The untagged remainder is reported as
    explicitly unmeasured rather than silently assumed covered.

  * :func:`flag_divergences` — an on-demand **divergence flagger** (LLM). For a
    derived question matched to the official catalogue on a shared concept, it asks
    whether the derived keyed answer *contradicts* what the official catalogue
    establishes. It emits disagreements for a human to review — NOT a pass/fail
    score: the harmonised codes are harmonised, *not identical*, so a flag may be a
    legitimate national derogation rather than an error. Costs tokens; ``--deep``.

The concept checklist below is a deliberately auditable *starting point* (like the
keyword sets in :mod:`src.scope`): every concept names itself and carries the
harmonised base it belongs to. Extend it as the banks grow.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from dataclasses import dataclass

from . import scope
from .questions import schema as qschema

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

# The official ground-truth bank, and the derived banks it validates. Each maps to
# the SQLite file(s) that hold the built bank (a country may ship several tracks).
OFFICIAL = "DE"
BANK_FILES: dict[str, list[str]] = {
    "DE": ["questions.de.sqlite"],                       # official ELWIS catalogue
    "CH": ["questions.ch.sqlite"],                       # derived from Swiss law
    "FR": ["questions.fr_cotiere.sqlite",                # derived from French law
           "questions.fr_eaux_interieures.sqlite"],
}
# A CH question is stored once per content language (fr/de/it); DE and FR are
# single-language. Comparing raw counts would make CH look 3× as broad and would
# adjudicate every Swiss question three times — so each bank is collapsed to one
# comparison language (its canonical one). The flagger is cross-lingual anyway
# (the official side is always German), and the concept keywords match either tongue.
BANK_LANG: dict[str, str] = {"DE": "de", "CH": "fr", "FR": "fr"}


# --------------------------------------------------------------------------
# The harmonised concept checklist
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Concept:
    id: str
    base: str            # which harmonised base this concept lives on
    label: str
    pattern: "re.Pattern"


def _c(cid: str, base: str, label: str, *keywords: str) -> Concept:
    # One combined FR|DE(|IT) pattern per concept — a concept's French keywords
    # won't match German text and vice-versa, so the union matches each bank in its
    # own language without per-language bookkeeping.
    return Concept(cid, base, label,
                   re.compile("|".join(keywords), re.I))


# CEVNI — the harmonised INLAND code (DE-Binnen ⟷ CH inland / FR eaux intérieures).
# COLREGS — the harmonised MARITIME code (DE-See ⟷ FR côtière).
# Universal — portable seamanship shared by every track.
CONCEPTS: list[Concept] = [
    # --- CEVNI (inland) ---
    _c("blue_board", "cevni", "Blue board / overtaking sign",
       r"panneau bleu", r"flotteur bleu", r"blaue[rn]? (tafel|flagge)", r"bandiera blu"),
    _c("keep_right", "cevni", "Keep to the right / starboard side",
       r"rive droite", r"serrer (à|a) (tribord|droite)", r"rechte seite",
       r"rechts halten", r"steuerbordseite"),
    _c("sound_one_blast", "cevni", "Sound signal — one short blast",
       r"un son bref", r"ein kurzer ton", r"einen kurzen ton"),
    _c("lock_passage", "cevni", "Lock (écluse / Schleuse) passage",
       r"\b(é|e)cluse", r"\bschleuse", r"\bconca\b"),
    _c("buoyage_inland", "cevni", "Inland buoyage / fairway marks",
       r"chenal", r"bou(é|e)e", r"espar", r"fahrwasser", r"\btonne\b", r"schifffahrtszeichen"),
    _c("prohibition_sign", "cevni", "Prohibition sign",
       r"interdiction", r"interdit", r"verbot", r"verboten", r"divieto"),
    _c("wash_wave", "cevni", "Wash / wave-making duty",
       r"remous", r"batillage", r"wellenschlag", r"\bsog\b"),

    # --- COLREGS (maritime) ---
    _c("crossing_giveway", "colregs", "Crossing — give-way / stand-on",
       r"privil(é|e)gi(é|e)", r"route.*crois", r"ausweichpflicht", r"wegerecht",
       r"kurse.*kreuzen", r"kreuzende kurse"),
    _c("head_on", "colregs", "Head-on situation",
       r"face (à|a) face", r"\bde front\b", r"entgegengesetzt", r"genau.*entgegen"),
    _c("overtaking_sea", "colregs", "Overtaking at sea",
       r"rattrapant", r"d(é|e)passement", r"\b(ü|u)berhol"),
    _c("restricted_visibility", "colregs", "Restricted visibility",
       r"visibilit(é|e) r(é|e)duite", r"\bbrume\b", r"verminderte sicht",
       r"unsichtigem wetter", r"\bnebel\b"),
    _c("distress_signals", "colregs", "Distress signals",
       r"d(é|e)tresse", r"notzeichen", r"notsignal", r"seenot"),

    # --- Universal seamanship ---
    _c("knots", "universal", "Knots / matelotage",
       r"\bn(œ|oe)ud", r"\bknoten\b", r"palstek", r"\bstek\b", r"\bnodo\b"),
    _c("beaufort", "universal", "Beaufort scale / wind force",
       r"beaufort", r"windst(ä|a)rke"),
    _c("lifejacket", "universal", "Lifejacket",
       r"gilet de sauvetage", r"rettungsweste", r"giubbotto"),
]


# --------------------------------------------------------------------------
# Loading + scoping the banks
# --------------------------------------------------------------------------

def load_bank(code: str) -> list:
    """A country's built bank, collapsed to its single comparison language (see
    :data:`BANK_LANG`) so counts are one-per-logical-question across banks. Missing
    bank files are skipped (the bank may not be built locally)."""
    lang = BANK_LANG.get(code)
    out: list = []
    for fn in BANK_FILES.get(code, []):
        path = os.path.join(DATA, fn)
        if not os.path.exists(path):
            continue
        conn = qschema.connect(path)
        out += [q for q in qschema.load_questions(conn)
                if lang is None or getattr(q, "lang", lang) == lang]
        conn.close()
    return out


def _haystack(q) -> str:
    p = q.provenance
    return " ".join((q.stem or "", getattr(p, "ref", "") or "",
                     getattr(p, "source", "") or "")).lower()


def _principle(q) -> str:
    """The question's deterministic principle tag (see src.questions.principles),
    or "" if untagged. This is the second — and far broader — shared instrument:
    unlike the hand-written concept checklist it is applied identically to every
    bank at build time, so it can compare derived banks to the official one over a
    much larger slice of the catalogue."""
    return getattr(q, "principle", "") or ""


def _base_questions(code: str) -> dict[str, list]:
    """The bank's questions bucketed by harmonised base (only the shareable
    universal/cevni/colregs scopes; national/local overlays are dropped)."""
    buckets: dict[str, list] = {b: [] for b in scope.BASES}
    for q in load_bank(code):
        s = scope.classify(q)
        if s in buckets:
            buckets[s].append(q)
    return buckets


# --------------------------------------------------------------------------
# Instrument 1 — deterministic coverage
# --------------------------------------------------------------------------

def coverage(derived: tuple[str, ...] = ("CH", "FR")) -> dict:
    """Compare each derived bank's harmonised-base coverage to the official one.

    Returns a report with:
      * ``counts`` — per-base question counts per bank;
      * ``matrix`` / ``gaps`` / ``absent_tracks`` — the hand-curated concept probe:
        per concept how many questions each bank carries, the concepts the official
        bank tests that a derived bank lacks, and tracks a bank doesn't implement;
      * ``instrumentation`` — per base, how much of the official bank is topic-tagged
        (the measurable slice; the rest is explicitly unmeasured);
      * ``principle_cov`` — per derived bank per base, the bounded coverage figure on
        that instrumented slice (topics + frequency-weighted), with missing topics.
    """
    codes = [OFFICIAL, *derived]
    banks = {c: _base_questions(c) for c in codes}
    counts = {b: counts for c in codes
              for b, counts in [(c, {base: len(banks[c][base]) for base in scope.BASES})]}

    # A base the derived bank has *no* questions in is an absent *track*, not a
    # gap: Switzerland is inland-only, so its empty `colregs` is by design — we must
    # not nag it concept-by-concept for a maritime code it never implements. Such a
    # base is excluded from gap detection and reported separately.
    absent: list[dict] = []
    for c in derived:
        for base in scope.BASES:
            if counts[c][base] == 0 and counts[OFFICIAL][base] > 0:
                absent.append({"bank": c, "base": base})
    absent_pairs = {(a["bank"], a["base"]) for a in absent}

    matrix: list[dict] = []
    gaps: list[dict] = []
    for concept in CONCEPTS:
        row = {"concept": concept.id, "base": concept.base, "label": concept.label,
               "by_bank": {}}
        for c in codes:
            n = sum(1 for q in banks[c][concept.base]
                    if concept.pattern.search(_haystack(q)))
            row["by_bank"][c] = n
        matrix.append(row)
        off = row["by_bank"][OFFICIAL]
        for c in derived:
            if (c, concept.base) in absent_pairs:
                continue                          # whole track absent — not a gap
            if off > 0 and row["by_bank"][c] == 0:
                gaps.append({"bank": c, "concept": concept.id,
                             "base": concept.base, "label": concept.label,
                             "official_count": off})
    # --- topic instrumentation + bounded coverage (the principle layer) -------
    # The hand-written concept checklist above is precise but tiny: it matches only
    # a sliver of the official bank, so on its own it can flag illustrative gaps but
    # cannot state a coverage *figure*. The deterministic `principle` tag reaches far
    # more of the catalogue, so we use it to report two honest numbers:
    #   (a) instrumentation — what fraction of the official bank ANY instrument can
    #       even see, per base. A coverage figure must never be read as covering more
    #       than this; the untagged remainder is genuinely unmeasured.
    #   (b) coverage — on that instrumented slice, how much of what the official bank
    #       tests (weighted by how often it tests it) the derived bank also carries.
    instrumentation: dict[str, dict] = {}
    for base in scope.BASES:
        offq = banks[OFFICIAL][base]
        concepts = [c for c in CONCEPTS if c.base == base]
        seen = sum(1 for q in offq
                   if _principle(q)
                   or any(c.pattern.search(_haystack(q)) for c in concepts))
        instrumentation[base] = {
            "official": len(offq), "instrumented": seen,
            "pct": round(100 * seen / len(offq), 1) if offq else None}

    principle_cov: dict[str, dict] = {}
    for c in derived:
        per_base: dict[str, dict] = {}
        for base in scope.BASES:
            # Skip a track the derived bank doesn't implement (CH has no maritime
            # code) and a base the official bank itself doesn't test.
            if (c, base) in absent_pairs or counts[OFFICIAL][base] == 0:
                continue
            off_weights: dict[str, int] = {}
            for q in banks[OFFICIAL][base]:
                p = _principle(q)
                if p:
                    off_weights[p] = off_weights.get(p, 0) + 1
            present = {_principle(q) for q in banks[c][base] if _principle(q)}
            covered = set(off_weights) & present
            w_off = sum(off_weights.values())
            w_cov = sum(n for p, n in off_weights.items() if p in covered)
            per_base[base] = {
                "topics_official": len(off_weights),
                "topics_covered": len(covered),
                "missing": sorted(set(off_weights) - present),
                "weighted_official": w_off,
                "weighted_covered": w_cov,
                "pct": round(100 * w_cov / w_off, 1) if w_off else None}
        principle_cov[c] = per_base

    return {"codes": codes, "counts": counts, "matrix": matrix,
            "gaps": gaps, "absent_tracks": absent,
            "instrumentation": instrumentation, "principle_cov": principle_cov}


def format_coverage(report: dict) -> str:
    codes = report["codes"]
    derived = [c for c in codes if c != OFFICIAL]
    lines = ["Harmonised-core coverage vs the official German catalogue",
             f"({OFFICIAL} is the official ELWIS catalogue; "
             f"{'/'.join(derived)} are derived from national law, fidelity unproven.)",
             ""]
    # Base counts table.
    head = "  base        " + "".join(f"{c:>8}" for c in codes)
    lines += [head, "  " + "-" * (len(head) - 2)]
    for base in scope.BASES:
        lines.append("  " + f"{base:10}" + "  " +
                     "".join(f"{report['counts'][c][base]:>8}" for c in codes))

    # --- 1. Measured slice: how much of the official bank we can even see -------
    instr = report.get("instrumentation", {})
    if instr:
        lines += ["", "  Measured slice — fraction of the official bank that is "
                      "topic-instrumented", "  (any coverage figure below speaks to "
                      "THIS slice only; the rest is unmeasured):"]
        for base in scope.BASES:
            d = instr.get(base)
            if not d or not d["official"]:
                continue
            pct = f"{d['pct']:.0f}%" if d["pct"] is not None else "n/a"
            lines.append(f"    {base:10} {d['instrumented']:>4}/{d['official']:<4} "
                         f"({pct}) topic-tagged")
        lines.append("    The untagged remainder (prose-heavy traffic-rule items) is "
                     "UNMEASURED — a derived")
        lines.append("    bank could be complete or sparse there and this instrument "
                     "cannot tell.")

    # --- 2. Coverage on the instrumented slice (the bounded number) ------------
    pcov = report.get("principle_cov", {})
    if pcov:
        lines += ["", "  Coverage on the topic-instrumented slice — share of what the "
                      "official bank tests",
                  "  (weighted by frequency) that the derived bank also carries. "
                  "Conservative by design:",
                  "  one principle tag per question, so a topic can read as missing "
                  "when its content is",
                  "  folded into a neighbour — read a low score as a FLOOR, not a verdict:"]
        for c in derived:
            for base in scope.BASES:
                d = pcov.get(c, {}).get(base)
                if not d or d["pct"] is None:
                    continue
                miss = (f"   missing: {', '.join(d['missing'])}"
                        if d["missing"] else "")
                lines.append(
                    f"    {c} {base:8} {d['pct']:>5.0f}%  "
                    f"({d['topics_covered']}/{d['topics_official']} topics, "
                    f"{d['weighted_covered']}/{d['weighted_official']} weighted){miss}")

    # --- 3. Fine-grained concept probe (hand-curated; low reach by design) -----
    lines += ["", "  Fine-grained concept probe — a hand-curated checklist. It "
                  "instruments only a small",
              "  part of the official bank (see the measured-slice line above), so "
              "its gaps are",
              "  illustrative spot-checks, NOT a coverage measure:"]
    lines += ["", "  concept (base)                 " + "".join(f"{c:>8}" for c in codes)]
    for row in report["matrix"]:
        label = f"{row['concept']} ({row['base']})"
        lines.append(f"  {label:30}" + "".join(f"{row['by_bank'][c]:>8}" for c in codes))
    # Absent tracks (by design — e.g. inland-only Switzerland has no maritime code).
    if report.get("absent_tracks"):
        lines += ["", "  tracks not implemented (excluded from gap detection):"]
        for a in report["absent_tracks"]:
            lines.append(f"    {a['bank']} has no {a['base']} questions "
                         f"(track absent by design)")
    # Gaps (within the hand-curated probe only — explicitly bounded).
    if report["gaps"]:
        lines += ["", f"  {len(report['gaps'])} probe gap(s) — checklist concepts the "
                      f"official bank tests but the derived bank lacks:"]
        for g in report["gaps"]:
            lines.append(f"    {g['bank']}: {g['concept']} ({g['base']}) — "
                         f"official has {g['official_count']}")
    else:
        lines += ["", "  No gaps within the hand-curated probe — but note this probe "
                      "sees only the small",
                  "  instrumented fraction above, so this is NOT a clean bill of "
                  "coverage."]

    # --- Bottom line: bounded, never "ready" -----------------------------------
    lines += ["", "  Bottom line: coverage can be stated only for the topic-tagged "
                  "slice (~half of the",
              "  official harmonised bank); the untagged remainder is unmeasured. "
              "This is a coverage",
              "  floor, not an exam-readiness signal — do not present any derived "
              "bank as 'ready to pass'."]
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Human-facing surfaces — a committed lock the docs + offline player read
# --------------------------------------------------------------------------
# The full report above is a maintainer diagnostic. The country docs and the
# static player need a stable, compact, *committed* view they can read without
# the (gitignored) built banks present — exactly the role data/sources.lock.json
# plays for staleness. `coverage_summary` distils the report; `write_lock` /
# `load_lock` persist it so doc generation + the player are deterministic and
# offline.
LOCK_PATH = os.path.join(DATA, "coverage.lock.json")


def coverage_summary(report: dict | None = None, generated: str = "") -> dict:
    """A compact, serialisable view of :func:`coverage` for humans. Per *derived*
    bank, per base it implements: the bounded coverage ``pct``, the
    ``instrumented_pct`` that figure rests on, and the ``missing`` topics the
    official bank tests. The official bank (DE) is the yardstick, not a derived
    bank, so it is recorded only as ``official`` — never given a coverage score."""
    report = report or coverage()
    instr = report.get("instrumentation", {})
    banks: dict[str, dict] = {}
    for code, per_base in report.get("principle_cov", {}).items():
        tracks = {}
        for base, d in per_base.items():
            if d.get("pct") is None:
                continue
            slice_pct = (instr.get(base) or {}).get("pct")
            tracks[base] = {
                "pct": round(d["pct"]),
                "instrumented_pct": round(slice_pct) if slice_pct is not None else None,
                "missing": list(d.get("missing", [])),
            }
        if tracks:
            banks[code] = {"tracks": tracks}
    return {"official": OFFICIAL, "generated": generated, "banks": banks}


def write_lock(path: str = LOCK_PATH, generated: str = "") -> dict:
    """Recompute the summary from the built banks and persist it (committed)."""
    summary = coverage_summary(generated=generated)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return summary


def load_lock(path: str = LOCK_PATH) -> dict:
    """Read the committed summary (no banks needed). Empty shell if absent."""
    if not os.path.exists(path):
        return {"official": OFFICIAL, "generated": "", "banks": {}}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------------------
# Instrument 2 — on-demand LLM divergence flagger
# --------------------------------------------------------------------------

def _correct_texts(q) -> list[str]:
    return [ch.text for ch in q.choices if ch.is_correct]


def _q_brief(q) -> str:
    correct = " / ".join(_correct_texts(q)) or "(no key)"
    return f"Q: {q.stem}\n  keyed answer: {correct}"


_ADJUDICATE_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string",
                    "enum": ["consistent", "diverges", "national_difference"]},
        "reason": {"type": "string"},
    },
    "required": ["verdict", "reason"],
}

_PROMPT = """You compare a DERIVED boat-licence exam question against an OFFICIAL \
catalogue on the SAME harmonised navigation rule ({base}: {label}).

The OFFICIAL catalogue (German ELWIS, ground truth) establishes this rule via:
{official}

The DERIVED question (from national law, fidelity unverified) is:
{derived}

Does the derived question's keyed answer CONTRADICT the harmonised rule the \
official catalogue establishes? Note: the inland (CEVNI) and maritime (COLREGS) \
codes are HARMONISED but not identical — a difference may be a legitimate national \
derogation, not an error. Reply with one of:
  - "consistent": the derived key agrees with the official rule.
  - "national_difference": they differ, but plausibly a real national derogation.
  - "diverges": the derived key appears WRONG against the harmonised rule.
Give a one-sentence reason."""


def _anthropic_adjudicator(model: str = "claude-sonnet-4-6"):
    import anthropic                              # lazy: importable without the SDK
    import json
    client = anthropic.Anthropic()

    def adjudicate(prompt: str) -> dict:
        msg = client.messages.create(
            model=model, max_tokens=400,
            tools=[{"name": "verdict", "description": "Emit the adjudication.",
                    "input_schema": _ADJUDICATE_SCHEMA}],
            tool_choice={"type": "tool", "name": "verdict"},
            messages=[{"role": "user", "content": prompt}])
        for block in msg.content:
            if getattr(block, "type", None) == "tool_use":
                return block.input
        raise RuntimeError("model returned no tool_use block")
    return adjudicate


def flag_divergences(derived_code: str, base: str = "cevni", limit: int = 20,
                     adjudicator=None, on_prompt=None) -> list[dict]:
    """Match derived questions to the official catalogue on a shared base+concept
    and ask the adjudicator whether each derived key contradicts the harmonised
    rule. Returns the non-"consistent" verdicts (the flags) for human review.

    `adjudicator` is a callable(prompt:str)->dict (so tests/dry-runs inject a fake,
    mirroring src.questions.prose). When None, the real Anthropic client is used.
    `on_prompt(prompt)` is called for each prompt before adjudication (for dry-run).
    """
    official_by_concept: dict[str, list] = {}
    for q in _base_questions(OFFICIAL)[base]:
        for concept in CONCEPTS:
            if concept.base == base and concept.pattern.search(_haystack(q)):
                official_by_concept.setdefault(concept.id, []).append(q)

    derived_buckets = _base_questions(derived_code)[base]
    if adjudicator is None and on_prompt is None:
        adjudicator = _anthropic_adjudicator()

    flags: list[dict] = []
    seen = 0
    for concept in CONCEPTS:
        if concept.base != base or concept.id not in official_by_concept:
            continue
        for dq in derived_buckets:
            if seen >= limit:
                return flags
            if not concept.pattern.search(_haystack(dq)):
                continue
            seen += 1
            official = "\n".join(f"  - {_q_brief(oq)}"
                                 for oq in official_by_concept[concept.id][:3])
            prompt = _PROMPT.format(base=base, label=concept.label,
                                    official=official, derived=_q_brief(dq))
            if on_prompt is not None:
                on_prompt(prompt)
                continue
            v = adjudicator(prompt)
            if v.get("verdict") != "consistent":
                flags.append({"bank": derived_code, "concept": concept.id,
                              "question_id": dq.id, "stem": dq.stem,
                              "verdict": v.get("verdict"), "reason": v.get("reason")})
    return flags
