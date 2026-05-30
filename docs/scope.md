# Question scope — the regime tree and the harmonised core

Navigation law composes by **lex specialis derogat legi generali**: the more
specific regime overrides the more general one, and what it does *not* override is
inherited from the broader set. So the regimes form one tree, each node a
**precision under a larger set** (its parent), and a question sits at the narrowest
rung that governs it:

```
UNIVERSAL                         seamanship valid on any water, any country
├─ CEVNI                          inland traffic code (signs/lights/sounds/rules)
│  ├─ CH-INLAND  (implements)     ONI/RNL — Switzerland
│  ├─ DE-INLAND  (implements)     BinSchStrO
│  ├─ FR-INLAND  (implements)     RGP — eaux intérieures
│  ├─ RHINE      (diverges)       CCNR / RheinSchPV
│  ├─ LEMAN      (diverges)       Franco-Swiss règlement
│  └─ BODENSEE   (excluded)       BSO — its own code; signage NOT portable
└─ COLREGS                        maritime traffic code (the sea base)
   ├─ DE-MARITIME (implements)    SeeSchStrO / KVR — SBF See, SKS, SSS
   └─ FR-MARITIME (implements)    RIPAM — option côtière
```

Two modules realise this, kept distinct:

* `src/jurisdictions.py` — the **regime tree**. Bases (`UNIVERSAL` → `CEVNI`,
  `COLREGS`), then one node *per country per track* (inland/maritime) **derived**
  from `src/countries`, then the shared/special waters declared by hand. Each node
  records its parent (`refines`) and how it sits under it (`relation`:
  `implements` / `diverges` / `excluded` / `is_base`). The **base ancestor** a node
  reaches (`base_of`) is its portability class.
* `src/scope.py` — the **question classifier**. It places each `Question` at one
  rung, country-agnostic and derived at build time.

## The scope taxonomy

`src/scope.py` assigns every `Question` exactly one scope — three **bases** (the
portable, shareable core) and two **overlays**:

| scope | kind | meaning | examples |
|---|---|---|---|
| `universal` | base | seamanship portable under *any* code | knots, generic weather, engine, first aid, environment |
| `cevni` | base | harmonised **inland** traffic code | inland signs/buoyage/lights/sounds, inland right-of-way |
| `colregs` | base | harmonised **maritime** traffic code | sea buoyage/lights, RIPAM/KVR collision rules |
| `national` | overlay | country statute | permit/registration/insurance law, bilateral frontier waters |
| `local` | overlay | tied to one water body | named local winds (Léman *bise*/*joran*…), an *excluded* regime (Bodensee/BSO) |

The **harmonised core** of a permit is `universal` + its track's base — `cevni` for
an inland permit, `colregs` for a sea permit. National/local are the overlay a
single country adds. The classifier is a deliberately **auditable heuristic**
(theme-keyed, refined by regexes on stem/ref/source — read `classify()`), run
narrowest-first (lex specialis), and a *starting point*: tune the keyword sets for
your own law.

## How it ships (and the byte-stability rule)

Scope is **derived, never stored** — computed at export time, so the `Question`
schema and the per-language national bundles
(`web/questions.{fr,de,it,en}.json`) are **untouched and byte-identical**. The core
ships as **additive** sibling files, one per base:

* `run.py` `cmd_web` builds `web/questions.<base>.<lang>.json` (the base's subset,
  `meta.pool = "<base>"`) for each base that has content, and lists them in
  `web/languages.json` under a `core` block (`{base: {lang: {path, count}}}`).
* The player (`web/app.js`) offers a **National ⟷ Common core** pool toggle. The
  core pool **composes** the available base bundles (universal + cevni + colregs)
  into one bank, deduped by id. The toggle hides itself when no core bundle exists.

> Invariant to preserve: after `python run.py web`, `git diff` must show **zero**
> change to the four national `questions.<lang>.json`. Only `languages.json`
> (additive keys) and the `questions.<base>.*.json` files may move.

## Adding a country to the core

A country joins the core for free as soon as its questions are in the bank:
`cmd_web` classifies every exportable question regardless of country/language. To
make the split accurate for a new country:

1. Confirm which tracks its permits cover. Set `Permit.track` (`inland` /
   `maritime`) on each permit in `src/countries/<code>.py`; when unset, the
   jurisdiction layer infers it from the permit code/label. Each track yields a
   regime node under `CEVNI` (inland) or `COLREGS` (maritime).
2. Skim `src/scope.py` and extend the keyword sets so *its* statute lands in
   `national`, *its* local waters in `local`, and *its* sea content in `colregs`
   (the `_MARITIME` markers). The defaults are tuned for Switzerland; a German or
   French bank needs its own admin/frontier/local/maritime vocabulary.
3. Run `python run.py web` and check the build summary's `harmonised core:` line +
   `scope.scope_counts()` look right (national statute should not leak into a base).

## Not CEVNI: Lake Constance (Bodensee), and divergent waters

Lake Constance is **explicitly outside CEVNI** — its tri-national
*Bodensee-Schifffahrts-Ordnung* (BSO) and *Bodenseeschifferpatent* replace the
inland code, so its signage is **not** portable. This is **wired**, not just
documented: `BODENSEE` is a `shared_water` jurisdiction with `relation =
"excluded"`, and `classify()` calls `jurisdictions.excluded_regime()` first — so
any BSO-sourced question is scoped `local` and can never enter a base, whatever its
theme. To add another *excluded* regime later, declare it in `src/jurisdictions.py`
and add its marker to `_EXCLUDED_MARKERS`; no change to `src/scope.py` is needed.

Bodensee is one instance of a **category**. The Rhine (`RHINE`, CCNR/RheinSchPV)
and the Léman (`LEMAN`, Franco-Swiss) also have their own regimes, but they merely
**diverge** from CEVNI (own deviations over a CEVNI base) rather than replace it —
so they keep `relation = "diverges"` and their harmonised signage *stays* in the
core. Only `excluded` regimes are guarded out.

## Files

* `src/jurisdictions.py` — the regime tree (`get`, `codes`, `base_of`, `relation`,
  `track`, `ancestors`, `excluded_regime`, `as_manifest`).
* `src/scope.py` — `classify`, `core_bank`, `ids_by_base`, `bases_present`,
  `scope_counts`, `SCOPES`/`BASES`/`OVERLAYS`.
* `tests/test_jurisdictions.py`, `tests/test_scope.py` — the contracts.
* `run.py` `cmd_web` — the additive per-base core bundles + the `core` manifest.
* `web/app.js` — the pool-composing `fetchBank` + `poolAvailable`/`selectPool`.
