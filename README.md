# Boat-permit — learn boating rules from verified sources

**Languages:** [English](README.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Italiano](README.it.md)

An open framework for studying **national boating-licence theory exams** built
**only** from public-domain law and clearly-reusable references. It covers three
countries today — **🇫🇷 France · 🇩🇪 Germany · 🇨🇭 Switzerland** — behind one
pipeline and one player, and it is designed so adding a country is one new file,
not a fork.

For each country it ships three things:

1. a structured, versioned **knowledge base** (KB) derived from that country's law,
2. a **source-cited practice-question bank**, and
3. a dependency-free **static player** (browser / GitHub Pages) with **Anki** and
   **Moodle GIFT** exports.

## The legal boundary (the whole point)

Every official exam is backed by a question bank, and the paid prep apps repackage
it. This project deliberately **does not touch any of that**. The hard rule, applied
identically in every country:

- **It ingests** only law and references that are public-domain or carry an explicit
  reuse licence. Provenance + a licence note are stored on **every** unit and **every**
  question.
- **It never scrapes, stores, or reproduces** a proprietary question bank or any paid
  app's questions/explanations.
- **Every practice question is derived from primary sources** and carries a citation
  back to the article, rule or figure it came from. Authoring a question from memory
  is forbidden — the source is the authority.

How that rule lands per country:

| Country | Law basis (public/reusable) | Question basis |
|---------|-----------------------------|----------------|
| 🇫🇷 **France** | Légifrance / DILA LEGI under **Licence Ouverte / Etalab** (French official acts carry no copyright) | Derived from the ingested law — the proprietary operator QCM banks (La Poste/Dekra/SGS/Bureau Veritas) are **never** touched |
| 🇩🇪 **Germany** | gesetze-im-internet.de XML, public-domain under **§5(1) UrhG** | The official **ELWIS** *amtliche Fragenkataloge* are reusable verbatim under **§5(2) UrhG** (cite www.elwis.de, no modification) — ingested as-is |
| 🇨🇭 **Switzerland** | Fedlex Akoma Ntoso XML, Swiss federal law is public-domain | Derived from the law — the asa-licensed bank repackaged by the paid apps is **never** touched |

## Quick start

```bash
pip install -r requirements.txt

# France — permis plaisance (seed + law-derived, Licence Ouverte)
python run.py fr

# Germany — Sportbootführerschein (federal law + ELWIS catalogues)
python run.py build     --country DE
python run.py questions --country DE

# Switzerland — cat-A motorboat (Fedlex law + derived questions)
python run.py build
python run.py questions

# the harmonised codes shared by every country (see below)
python run.py build --country INT

# bundle every built bank + assets into the static player
python run.py web
python -m http.server -d web 8000   # http://localhost:8000
```

KB builds are cached and re-runnable; `--force` re-fetches. The question and web
steps are pure transforms over the previous outputs.

## How it works

The pipeline is the same for every country; only the per-country descriptor changes.

### Phase 1 — knowledge base

Three independently re-runnable stages, each reading the previous one's output:

| Stage | Command | What it does |
|-------|---------|--------------|
| **Fetch** | `run.py fetch [--country X]` | Pulls raw sources into `data/raw/<id>/`, verbatim, with a `manifest.json` recording URL + retrieval date + legal version. Never re-fetches unless `--force`. |
| **Parse** | `run.py parse [--country X]` | Turns each raw source into structured `KnowledgeUnit`s (pure, no network). One parser per source type — Akoma Ntoso (CH), gii XML (DE), LEGI XML (FR), COLREG PDF (INT), MediaWiki/HTML. |
| **Normalize** | (part of `build`) | Merges into one SQLite KB, localizes image assets, links articles ↔ figures, tags every unit to that country's exam theme, stamps a version. |

Limit to specific sources with `--only`. Each country's law (signs, buoyage, lights,
sound signals) carries the diagrams as localized image assets, captioned from the
annex tables and linked to the citing articles.

### Phase 2 — question bank

| Step | Command | What it does |
|------|---------|--------------|
| **Figures** | `run.py questions` | Deterministically generates figure-recognition questions from captioned annex diagrams. Confusion-set distractors keyed by signal type; sha1-seeded so output is stable. Auto-approved. |
| **Derive / draft** | `run.py draft …` · `run.py fr` | Drafts questions strictly **from ingested source text** (a lexical grounding guard drops likely hallucinations), each pinned to an authoritative citation. Lands as **`pending`**. |
| **Catalogue ingest** | `run.py questions --country DE` | Ingests an official reusable catalogue (Germany's ELWIS) **verbatim**, each question tagged + carrying its §5 attribution. |
| **Review** | `run.py review --list / --approve / --reject` | Human review gate. Only `auto_approved` + `approved` questions are ever exported. |
| **Web** | `run.py web` | Re-exports every approved bank to `questions.<lang>.json`, bundles the figure assets into `web/`, and writes the per-language **Anki decks** (`web/anki/`) + **Moodle GIFT** files (`web/gift/`). |

## The countries

All three are first-class: each is one descriptor in `src/countries/` declaring its
law sources, exam-theme taxonomy + tagger, permit catalogue, exam rules and regional
regimes — the config the pipeline consumes. Adding a country is one new file + one
registry line (`src/countries/registry.py`), so parallel work doesn't collide.

### 🇫🇷 France — permis plaisance

The **permis plaisance** in two options: **côtière** (maritime, ≤6 NM from a shelter,
day and night) and **eaux intérieures** (rivers, canals, lakes). The exam is national
— **40 single-answer QCM, pass at ≤5 errors (35/40), ~30 min**, identical everywhere
(no regional variance). France is **seed- + law-derived**: questions are authored
**from** the ingested French law, never from the proprietary operator banks.

- **Law (Licence Ouverte / Etalab):** the project ingests the bulk **DILA LEGI** open
  data — the France analogue of Fedlex — for the **Code des transports, Part 4** (the
  RGP, France's CEVNI implementation), the **Code de l'environnement** (MARPOL/rejets),
  the **décret & arrêté du 28 sept. 2007** (the référentiel), and **Division 245**
  (≈1,346 in-force articles). Maritime grounding that LEGI doesn't carry — **RIPAM/
  COLREG, IALA Region A buoyage, SHOM** tides/datums — is ingested as a verified
  reference-fact corpus (facts aren't copyrightable; each cited to its primary source).
- **Build:** `python run.py fr` → both option banks + the `web/fr/` players.

### 🇩🇪 Germany — Sportbootführerschein

Germany's **Sportbootführerschein**, with the richest catalogue of the three.

- **Law (§5(1) UrhG, public-domain):** gesetze-im-internet.de serves each ordinance as
  structured XML at `<slug>/xml.zip`. `run.py build --country DE` pulls **SeeSchStrO,
  BinSchStrO, the KVR/COLREG, the SpFV and the RheinSchPV** (≈1,750 article units incl.
  buoyage/light/sign diagrams), tagged to a German taxonomy (Verkehrsregeln,
  Schifffahrtszeichen, Lichter/Signale, Wetterkunde, …).
- **Official catalogue (§5(2) UrhG, reusable):** unlike the off-limits Swiss bank, the
  **ELWIS** *amtliche Fragenkataloge* for SBF See/Binnen are reusable *"solange der
  Inhalt unverändert bleibt und als Quelle www.elwis.de angegeben wird"*.
  `run.py questions --country DE` ingests both catalogues **verbatim** (≈515 questions
  after deduping the shared Basisfragen), each tagged to a theme + exam block with the
  §5 attribution on its provenance. Because reuse is conditional on *no modification*,
  the German bank is German-only and options are only **re-ordered** for display, never
  reworded.
- **Permits & exam:** the federal **SBF See / SBF Binnen** (motor / sail / both), the
  voluntary **SKS / SSS / SHS**, and the trinational **Bodensee-Schifferpatent**.
  Grading is **block-based** (e.g. ≥5/7 Basis **and** ≥18/23 spezifisch), in
  `questions/schema.py:grade_exam_blocks`. Buoyage is **IALA Region A**. A 2025–26
  reform is flagged as *pending*, not settled law (`countries/de.py:REFORM_NOTE`).
- **Player:** the countrybar's **🇩🇪 Deutschland** opens `web/de/`, where a permit picker
  drives the real **block-structured exam**.

### 🇨🇭 Switzerland — cat-A motorboat (+ cat-D scaffold)

The **category-A motorboat** theory exam, standardized intercantonally by the **VKS**
(Geneva's OCV administers the national standard on Lac Léman).

- **Law (public-domain):** Fedlex pages are JS-rendered, so the page HTML is never
  scraped — the build resolves the **Akoma Ntoso XML** (article text) and its annex
  images via the Fedlex **SPARQL endpoint** + filestore. Sources: the **ONI**
  (RS 747.201.1) and the **RNL** (Léman, RS 747.221.1), plus freely-licensed météo and
  matelotage references.
- **Exam:** **60 questions · 50 minutes · 180 points · pass at 165/180.** Each question
  has 3 answers of which **1–2 are correct** (multi-select), scored **all-or-nothing**.
  The only per-canton variance is the **time limit** (50 min GE/VD · 45 min Bern),
  modelled in `src/cantons.py` and surfaced as a **canton picker** in the player.
- **Permits:** **cat-A** is the fully-grounded six-theme target (Définitions,
  Météorologie, Lois, Signalisation, Matelotage, Eaux frontalières). **cat-D** (voile)
  is scaffolded — it shares the cat-A core and adds a `voile` theme, awaiting a
  freely-licensed sailing-technique source.
- **Build:** `python run.py build` + `python run.py questions` → `web/` (the default,
  so a bare build is the Swiss build).

## Harmonised codes — the supra-national layer (`INT`)

Above the national exams sit the **harmonised navigation codes** every country's bank
shares: **COLREGS** (maritime collision rules) and **CEVNI** (the European inland-
waterways code) — the roots of the regime tree in `src/jurisdictions.py`. The `INT`
registry member (`src/countries/intl.py`) grounds them in their **canonical text**
rather than only indirectly via national enactments. It is sourcing-only — no permits,
no player bundle — so it never appears in the country picker.

- **COLREG — ingested.** The verbatim International Regulations (1972) are a
  **US-Government work** (public domain, 17 USC §105) as published by the US Coast
  Guard. `run.py build --country INT` fetches the USCG "Navigation Rules" PDF and the
  parser (`src/parsers/colreg.py`) keeps only its *International* pages, segmenting the
  38 Rules + Annexes I–IV. The IMO's copyrighted consolidated edition is **not** used.
- **CEVNI — not ingested (licence barrier).** The canonical UNECE text (Resolution
  No. 24, Rev.6) is all-rights-reserved: UN policy requires written permission and
  forbids redistribution/derivatives, so it fails the project's reuse rule. It is
  recorded as a `Reference`; a reproduction-permission request has been sent to UNECE
  and is pending. Until granted, the CEVNI base stays grounded via the public-domain
  national inland enactments already ingested.

### Shared core vs national bank

Because so much content is harmonised, every question is classified at build time
(`src/scope.py`) as one of `universal` (seamanship/weather/first-aid) · `cevni`
(inland code) · `colregs` (maritime code) · `national` (statute) · `local` (one water
body). The portable bases are pooled across **all** countries' banks per language into
additive `web/questions.<base>.<lang>.json` bundles, and the player's
**National ⟷ Common-core** toggle composes `universal + (cevni | colregs)` for the
active permit's track. National bundles stay **byte-identical** across builds — a
tracked invariant. See `docs/scope.md`.

## The player

`web/` is dependency-free vanilla JS. It loads the active language's bank, reads the
exam config from its `meta`, and runs a chronometered **exam** and a **practice** mode
with source-cited corrections. You can **study by domain** (toggle which themes a run
draws from), flip the **National ⟷ Common-core** pool, and the results screen breaks
the **score down per domain**. The **🇫🇷 / 🇩🇪 / 🇨🇭 countrybar** switches between the
national players, each reusing the same engine with its own exam rules. The player also
offers the **Anki deck** and **Moodle GIFT** file for the active language as one-click
downloads.

### Languages

The player UI is translated into **French, German, Italian and English**, and question
content is built per-language. Where a country's official law isn't published in a
language (e.g. English nowhere, Italian only in CH), the bank is flagged **unofficial**
or falls back to the operative language with a visible notice. UI strings live in
`web/i18n.js`; `run.py web` emits one `questions.<lang>.json` per language plus a
`languages.json` manifest.

### Anki & Moodle exports

| Tool | Command | What it does |
|------|---------|--------------|
| **Anki** | `python tools/anki.py export [lang]` | A real `.apkg` (zip + SQLite, figures bundled, one **subdeck per theme**) and an editable `.tsv`. `import file.tsv --apply` folds edits back as **pending** drafts. Stdlib only. |
| **GIFT** | `python tools/gift.py export [lang]` | A **Moodle GIFT** file, one `$CATEGORY` per theme, figures embedded as base64 `data:` URIs so it's self-contained. Stdlib only. |

The Anki mapping is **lossless for editable text** but **structure-locked**: which
options are correct, the image, and provenance stay owned by the bank, so an edit
re-imported from Anki/TSV can never silently flip an answer — it lands as a `pending`
draft for re-review. All package ids are content-derived (sha1) and mtimes pinned, so a
rebuild is byte-identical.

## Layout

```
run.py                 CLI orchestrator (build / questions / draft / review / fr / web)
src/
  sources.py           approved source registry (provenance + licence)
  fetch.py             stage 1 — fetch + cache (Fedlex SPARQL, gii xml.zip, DILA LEGI,
                         USCG PDF, MediaWiki API, HTTP)
  parse.py             stage 2 — dispatch to parsers
  parsers/             Akoma Ntoso (CH), gii (DE law XML), COLREG PDF (INT), prose, HTML
  normalize.py         stage 3 — merge -> SQLite + asset localization
  schema.py            KnowledgeUnit + SQLite DDL + JSON export
  themes.py / cantons.py   CH exam taxonomy + per-canton time variance
  countries/           country registry — ch.py / de.py / fr.py / intl.py + registry.py
                         (sources, tagger, themes, permits, regions) consumed by pipeline
  jurisdictions.py     the lex-specialis regime tree (universal -> cevni/colregs -> ...)
  scope.py             classify each question (universal/cevni/colregs/national/local)
  fr/                  France content modules (seed, LEGI ingest, derivation, references)
  questions/
    schema.py          canonical question schema, scoring (incl. block grading), export
    figures.py         templated figure-recognition generator
    elwis.py           ingest the official German SBF catalogues verbatim (§5(2))
    prose.py / seed_prose.py   LLM-draft pipeline + grounding guard / seed questions
tools/
  anki.py / gift.py    Anki .apkg/.tsv + Moodle GIFT exporters (stdlib only)
  subagent_*.py        no-API-key drafting/figure/translation pipelines
web/                   dependency-free static player (index.html, app.js, style.css)
  fr/ · de/            the France and Germany players (shared engine, own bundles)
  anki/ · gift/        prebuilt per-language decks / GIFT files (in-page download)
tests/                 plain-assert tests (run: python tests/test_*.py)
data/                  generated (gitignored): raw cache, assets, *.sqlite, *.json
```

## Tests

```bash
for t in tests/test_*.py; do python "$t"; done
```

All offline; no network or API key needed.

## Licence

Tooling in this repo is open for reuse. Ingested content keeps its own licence,
recorded per unit and per question: Swiss/French federal law and the COLREG (USCG) are
public-domain; French open data is Licence Ouverte / Etalab; German law is §5(1) UrhG
and the ELWIS catalogue §5(2) UrhG (cite www.elwis.de, unmodified); Wikipedia matelotage
material is CC BY-SA 4.0; météo/cantonal pages are official sources used with
attribution.
