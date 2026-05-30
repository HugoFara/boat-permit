# Boat-permit — free study tool for the Swiss cat-A motorboat theory exam

A free, open study tool for the **Swiss category-A motorboat theory exam**
(Geneva / OCV, Lac Léman). It is built **only** from public-domain law and
clearly-reusable references, and it ships two things:

1. a structured, versioned **knowledge base** (KB) derived from the law, and
2. a **practice-question bank** (`questions.json`) plus a small **static player**
   you can open in a browser or host on GitHub Pages.

## Legal boundary (the whole point)

The official exam draws on an **asa-licensed** ~520-question bank, repackaged by
the paid prep apps (BoatDriver, iTheorie, theorie-bateau, …). This project
deliberately **does not touch any of that**.

- **It ingests:** the ONI and other federal/cantonal navigation law (Swiss
  federal law is public-domain and freely reusable), plus freely-licensed météo
  and matelotage references. Provenance + a licence note are stored on every unit.
- **It never scrapes, stores, or reproduces:** the asa question bank, or any paid
  app's questions/explanations.

Every practice question is **derived from primary sources** and carries a citation
back to the article or figure it came from.

## Quick start

```bash
pip install -r requirements.txt

python run.py build        # fetch + parse + normalize law -> data/kb.sqlite (+ kb.json)
python run.py questions    # derive templated figure questions -> data/questions.sqlite
python run.py web          # bundle the approved bank + assets into web/

# then open the player:
python -m http.server -d web 8000   # http://localhost:8000
```

The KB build is cached and re-runnable; `--force` re-fetches everything. The
question and web steps are pure transforms over the previous outputs.

## How it works

### Phase 1 — knowledge base (`run.py build`)

Three independently re-runnable stages, each reading the previous one's output:

| Stage | Command | What it does |
|-------|---------|--------------|
| **Fetch** | `python run.py fetch` | Pulls raw sources into `data/raw/<id>/`, verbatim, with a `manifest.json` recording URL + retrieval date + legal version. Never re-fetches unless `--force`. |
| **Parse** | `python run.py parse` | Turns each raw source into structured `KnowledgeUnit`s (pure, no network). One parser per source type. |
| **Normalize** | (part of `build`) | Merges into one SQLite KB, localizes image assets, links articles ↔ figures, tags every unit to an exam theme, stamps a version. |

Limit to specific sources with `--only oni,rnl`. The current KB holds **602
units** across articles, annex figures, and prose sections.

**Law fetch:** Fedlex pages are JS-rendered, so we never scrape the page HTML.
We resolve the **Akoma Ntoso XML** (article text) and its referenced annex images
via the Fedlex **SPARQL endpoint** + filestore. The XML images carry the
signalisation diagrams (lights, buoys, boards), captioned from their annex tables
(181/181 figures captioned, linked to the citing articles).

### Phase 2 — question bank + player

| Step | Command | What it does |
|------|---------|--------------|
| **Figures** | `python run.py questions` | Deterministically generates figure-recognition questions from the captioned annex diagrams. Confusion-set distractors keyed by signal type; sha1-seeded so the output is stable. Auto-approved. |
| **Draft** | `python run.py draft --theme … ` | Drafts prose questions with an LLM, strictly source-grounded (a lexical grounding guard drops likely hallucinations). Lands in the bank as **`pending`**. Needs an API key — see `requirements.txt`. A built-in **seed set** of hand-authored questions is available via `--seed`. |
| **Review** | `python run.py review --list / --approve / --reject` | Human review gate. Only `auto_approved` + `approved` questions are ever exported. |
| **Web** | `python run.py web` | Re-exports the approved bank to `questions.json`, bundles it with the figure assets into `web/`, and writes the per-language **Anki decks** (`web/anki/`) + **Moodle GIFT** files (`web/gift/`) the player offers as downloads. |
| **Anki** | `python tools/anki.py export [lang]` | Exports the bank to a real `.apkg` (zip + SQLite, figures bundled, one **subdeck per theme**) and an editable `.tsv`. `python tools/anki.py import file.tsv --apply` folds edits back as **pending** drafts. Standard library only. |
| **GIFT** | `python tools/gift.py export [lang]` | Exports the bank to a **Moodle GIFT** file (`.gift`), one `$CATEGORY` per theme, figures embedded as base64 `data:` URIs so it's self-contained. Single-answer questions use `=`/`~`; the exam's two-correct questions use weighted `~%50%`. Standard library only. |

The bank currently exports **795 reviewed questions** across FR/DE/IT/EN
(figure-recognition + grounded prose + night-lighting rules), with more drafts
sitting behind the review gate.

**The player** (`web/`) is dependency-free vanilla JS. It loads the per-language
bank (`questions.<lang>.json`), reads the exam config from its `meta`, and runs two
modes: a chronometered **exam** (60 questions, balanced across themes) and a
**practice** mode with source-cited corrections. You can **study by domain**
(toggle which exam themes a run draws from) and the results screen breaks the
**score down per domain**. Scoring mirrors the real exam exactly. The player also
offers the **Anki deck** and a **Moodle GIFT** file for the active language as
one-click downloads, for study offline or in another platform. The UI ships in
four languages with a language switcher (see below).

#### Anki round-trip

An Anki note is `(guid, fields, tags, media)`. Mapping `Question` onto it pins the
schema to an SRS-friendly shape: a stable per-question id (→ the note GUID), a
clean front/back split, `theme`/`lang`/`kind` as tags, provenance on the card, and
figures as bundled media. The mapping is **lossless for the editable text** (stem,
choice texts, explanation) but **structure-locked**: which options are correct, the
image, and provenance stay owned by the bank, so an edit re-imported from Anki/TSV
can never silently flip an answer — it lands as a `pending` draft for re-review.
All package ids are derived from content (sha1) and zip mtimes are pinned, so a
rebuild is byte-identical.

### Languages

The exam is offered in the official Swiss languages; the player UI is translated
into **French, German, Italian, and English**, and question content is built
per-language:

| Lang | Official law source | Content status |
|------|---------------------|----------------|
| FR | ✅ Fedlex | grounded — the operative language for the Geneva/Léman exam |
| DE | ✅ Fedlex | grounded (planned) — same fetch pipeline, different ELI |
| IT | ✅ Fedlex | grounded (planned) — same |
| EN | ❌ none exists | unofficial study translation only (Swiss law isn't published in English) |

The figure PNGs are language-neutral; only captions/legends re-fetch per language.
The player loads the active language's bank and **falls back to French** (with a
visible notice) for any language whose bank isn't built yet. English content, when
present, is flagged **unofficial** — only the FR/DE/IT versions are authoritative.

The UI strings live in `web/i18n.js`; question language is the `lang` field on each
question, and `run.py web` emits one `questions.<lang>.json` per language plus a
`languages.json` manifest.

### Exam format (verified against official VKS / OCV sources)

**60 questions · 50 minutes · 180 points · pass at 165/180** (max 15 fault points,
≈ 5 fully-wrong questions). Each question has 3 answers of which **1–2 are correct**
(multi-select), scored **all-or-nothing** per question (3 pts only if the selected
set matches exactly). The exam is standardized intercantonally by the VKS; Geneva's
OCV administers this national standard. The 50-minute timer is the one cantonal
detail (Bern uses 45).

## Sources

| id | Source | Themes | Licence tier |
|----|--------|--------|--------------|
| `oni` | ONI — Ordonnance sur la navigation intérieure (RS 747.201.1) | Définitions, Lois, Signalisation (+ annexe figures) | public domain |
| `rnl` | Règlement de la navigation sur le Léman (RS 747.221.1) | Eaux frontalières, Signalisation | public domain |
| `matelotage_wp` | Wikipédia — nœuds marins | Matelotage | CC BY-SA 4.0 |
| `meteo_vents` | MétéoSuisse — Les vents du Léman | Météorologie | official, attribute |
| `meteo_signaux` | SISL — signaux d'avis de tempête | Météorologie / Signalisation | cross-check only |
| `geneve` | Genève — consignes générales de navigation | Lois (cantonal) | official, attribute |

## Exam theme taxonomy (normalization target)

1. Définitions · 2. Météorologie · 3. Lois sur la navigation en eaux intérieures ·
4. Signalisation et signaux acoustiques · 5. Matelotage · 6. Eaux frontalières

Tagging is rule-based and auditable (source default + keyword heuristics over
`ref`/`title`/`text`); see `src/themes.py`. It is intentionally easy to tune.

## Layout

```
run.py                 CLI orchestrator (build / questions / draft / review / web)
src/
  sources.py           approved source registry (provenance + licence)
  fetch.py             stage 1 — fetch + cache (Fedlex SPARQL, MediaWiki API, HTTP)
  parse.py             stage 2 — dispatch to parsers
  parsers/             Akoma Ntoso law, MediaWiki prose, generic HTML
  normalize.py         stage 3 — merge -> SQLite + asset localization
  schema.py            KnowledgeUnit + SQLite DDL + JSON export
  themes.py            exam taxonomy + tagging rules
  questions/
    schema.py          canonical question schema, scoring, review gate, JSON export
    figures.py         templated figure-recognition generator
    prose.py           LLM-draft pipeline + grounding guard
    seed_prose.py      hand-authored seed questions
tools/
  anki.py              Anki .apkg/.tsv export + round-trip import (stdlib only)
  gift.py              Moodle GIFT export, figures embedded as data URIs (stdlib)
  subagent_*.py        no-API-key drafting/figure/translation pipelines
web/                   dependency-free static player (index.html, app.js, style.css)
  anki/                prebuilt per-language Anki decks (in-page download)
  gift/                prebuilt per-language Moodle GIFT files (in-page download)
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
recorded per unit (see the Sources table). Federal/cantonal law is public-domain;
Wikipedia matelotage material is CC BY-SA 4.0; météo/cantonal pages are official
sources used with attribution.
