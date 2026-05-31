# Learning roadmap — from recognition to understanding

The app can already make someone *pass* the exam (multiple-choice recognition).
This roadmap is about making them *understand* — so a value like "750 N of buoyancy
per person" stops being an arbitrary number to memorise and becomes something the
learner can reconstruct and apply.

## The design principle that unlocks everything

The earlier framing treated "offline player vs. runtime model" as the fork that
gates the deep features. It isn't, because the pipeline **already calls an LLM at
build time** (`src/questions/prose.py` drafts questions behind the review gate). So
the architecture is:

> **Author rich content at build time (LLM + human review gate) → ship it static →
> the player stays 100 % offline and dependency-free.**

Every feature below keeps that property. No feature requires a runtime API key.

## Exam fidelity is preserved

The real exam is multiple-choice, so we must keep training recognition. Therefore
**all of this lands in practice mode**; exam mode keeps mirroring the real format
byte-for-byte. The split already exists in the player (`state.mode === "practice"`).

## The four groups

### Group A — The "why" layer  *(the core motivation)*

The existing `explanation` field is one sentence that *cites* the rule. It says
*what*, never *why*. Group A adds a separate, reusable **concept** content type — a
small set of generative explainers, each linked to the questions it underlies.

- **A1 — Physical / natural rationale.** Why fog forms, why a gust front arrives
  before the rain, why a displacement hull has a hull-speed limit, why 750 N keeps
  an unconscious adult's airway above water. Meteorology / physics, not law.
- **A2 — Legal-value rationale.** Why the law *picked* a number.
  **Policy (decided): sourced-only, never invented.** Where no source states the
  legislator's intent, explain *what the value guarantees* (derivable from physics
  or a cited standard) rather than guessing the intent. Same hard rule as questions:
  the source is the authority — see `memory/source-questions-never-recall.md`.

Mechanism: a `concept` record (id, title, body, source/provenance, linked question
ids + principle tag), surfaced in the player as a "Learn" card before/after the
questions that test it. New content type; highest effort; pure build-time + review.

### Group B — Turn existing MCQs into retrieval  *(player-side, cheap)*

- **B1 — Recall-first reveal.** In practice, show the stem first and make the
  learner commit (optionally jotting a free-text answer) *before* the options
  appear. Converts every existing question from recognition to recall. No data
  change.
- **B2 — Diagnostic distractor feedback.** On a wrong pick, name the specific
  confusion instead of just "the answer is B". *Nearly free for figure questions* —
  each distractor is itself another figure's caption, so we know what the wrong
  choice means and where it really comes from. For prose questions it uses a new
  per-choice `rationale` field, authored at build time (empty for now → graceful
  fallback to the chosen-vs-correct contrast).
- **B3 — Self-explanation (offline form).** Prompt "why?" → learner articulates →
  reveal the rule → self-score. The generation benefit survives without a grader.
  *(Deferred behind B1/B2.)*

### Group C — Durability  *(player-side, localStorage)*

- **C1 — Spaced repetition + interleaving.** Per-question history in `localStorage`
  (a Leitner box + last-seen timestamp). A "spaced review" practice ordering draws
  *due* and *weak* and *never-seen* items first, interleaved across themes
  (interleaving improves the signal discrimination this domain lives on).
- **C2 — Confidence capture + hypercorrection.** Ask confidence with each practice
  answer; prioritise **high-confidence-wrong** items for resurfacing and flag them
  in the review. Those are the dangerous-on-the-water errors, and once corrected
  they stick unusually well.

### Group D — Transfer  *(build-time LLM, highest payoff)*

- **D1 — Principle clustering.** Tag each question with the generative principle it
  tests (IALA buoyage logic, the short/long-blast grammar, the give-way hierarchy).
- **D2 — Scenario pools.** Build-time-generated *novel* scenarios grounded in the
  cited rule, review-gated, shipped static. Distractors become plausible
  *misapplications* of the rule. *(Builds on A's principle tags.)*

## Cost map (grounded in the actual code)

| Item | Data-model change | Player change | Offline | Effort |
|------|-------------------|---------------|:------:|:-----:|
| B1 recall-first | none | reveal flow | ✅ | XS |
| B2 figures | none (derive) | reveal | ✅ | S |
| B2 prose | `+ Choice.rationale` (additive) | reveal | ✅ | M (authoring) |
| C1 spacing | none (localStorage) | scheduler module | ✅ | M |
| C2 confidence | none (localStorage) | reveal UI + scheduler | ✅ | S |
| A why-layer | new `concept` type + link | "Learn" card | ✅ | L (content) |
| D transfer | `+ principle` tag + generator | scenario render | ✅ | L |

The schema is friendly to this: `src/questions/schema.py` already does additive
idempotent migrations (`_migrate`) and exports via `asdict`, so a new field flows
through to the player automatically.

## Sequence (decided)

1. **Phase 1 + 2 (this pass) — all player-side, offline, no content backlog:**
   B1 recall-first · B2 diagnostic feedback (figures now, `Choice.rationale` field
   wired for prose later) · C1 spaced + interleaved · C2 confidence + hypercorrection.
   Practice-mode settings persist in `localStorage`; exam mode untouched.
2. **Group A — the "why" content layer.** Design the `concept` type; pilot one
   theme end-to-end (meteorology for A1; buoyancy / 750 N for A2), then scale
   authoring through the review gate.
3. **Group D — transfer.** Principle tags → scenario pools.

## Settings the player gains (practice only)

A JS-built practice-settings panel (no per-country HTML change needed), each toggle
persisted in `localStorage`:

- **Recall-first** (B1)
- **Confidence rating** (C2)
- **Spaced review** ordering (C1)
</content>
</invoke>

result
File created successfully... (1 / 2 files)

Result too long, truncated to 1.0% of 30000. Please retry in a more targeted way if you need the full output.

Now `web/i18n.js` (line 134)
... (truncated because it is very long)
