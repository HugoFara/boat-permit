# Boat-permit study KB — Phase 1 (scraper + aggregator)

A free study tool for the **Swiss category-A motorboat theory exam** (Geneva /
OCV, Lac Léman), built **only** from public-domain law and clearly-reusable
references. It deliberately does **not** touch the asa-licensed exam question
bank or any paid app — see `boat-exam-app-handoff.md` for the full rationale.

Phase 1 (this repo) produces a clean, structured, normalized **knowledge base**.
Phase 2 (the exam app that derives practice questions) is not built yet.

## Quick start

```bash
pip install -r requirements.txt
python run.py build          # fetch + parse + normalize -> data/kb.sqlite (+ kb.json)
```

That's it. The build is cached and re-runnable; `--force` re-fetches everything.

## Pipeline

Three independently re-runnable stages, each reading the previous one's output:

| Stage | Command | What it does |
|-------|---------|--------------|
| **Fetch** | `python run.py fetch` | Pulls raw sources into `data/raw/<id>/`, verbatim, with a `manifest.json` recording URL + retrieval date + legal version. Never re-fetches unless `--force`. |
| **Parse** | `python run.py parse` | Turns each raw source into structured `KnowledgeUnit`s (pure, no network). One parser per source type. |
| **Normalize** | (part of `build`) | Merges into one SQLite KB, localizes image assets, links articles ↔ figures, tags every unit to an exam theme, stamps a version. |

Limit to specific sources with `--only oni,rnl`.

## Sources

All sources are public-domain law or clearly-reusable references (provenance and a
licence note are stored on every unit).

| id | Source | Themes | Licence tier |
|----|--------|--------|--------------|
| `oni` | ONI — Ordonnance sur la navigation intérieure (RS 747.201.1) | Définitions, Lois, Signalisation (+ annexe figures) | public domain |
| `rnl` | Règlement de la navigation sur le Léman (RS 747.221.1) | Eaux frontalières, Signalisation | public domain |
| `matelotage_wp` | Wikipédia — nœuds marins | Matelotage | CC BY-SA 4.0 |
| `meteo_vents` | MétéoSuisse — Les vents du Léman | Météorologie | official, attribute |
| `meteo_signaux` | SISL — signaux d'avis de tempête | Météorologie / Signalisation | cross-check only |
| `geneve` | Genève — consignes générales de navigation | Lois (cantonal) | official, attribute |

**Law fetch:** Fedlex pages are JS-rendered, so we never scrape the page HTML.
We resolve the **Akoma Ntoso XML** (article text) and its referenced annex
images via the Fedlex **SPARQL endpoint** + filestore. The XML images carry the
signalisation diagrams (lights, buoys, boards), captioned from their annex tables.

## Knowledge-unit schema

Stored in SQLite (`units` + child `assets`, `cross_refs` tables; also exported to
`data/kb.json`):

```
id, theme,                       # theme from the 6-item exam taxonomy
kind: article | annex_figure | prose_section
ref,                             # "ONI art. 23" / "ONI Annexe 2 – fig. 29"
title, text,
source_id, source_name, source_url, retrieved, legal_version, licence,
assets:     [ {type:"image", path, caption} ],
cross_refs: [unit_id...]         # e.g. article -> its annex figure
```

## Exam theme taxonomy (normalization target)

1. Définitions · 2. Météorologie · 3. Lois sur la navigation en eaux intérieures ·
4. Signalisation et signaux acoustiques · 5. Matelotage · 6. Eaux frontalières

Tagging is rule-based and auditable (source default + keyword heuristics over
`ref`/`title`/`text`); see `src/themes.py`. It is intentionally easy to tune.

## Layout

```
run.py                 CLI orchestrator
src/
  sources.py           approved source registry (provenance + licence)
  fetch.py             stage 1 — fetch + cache (Fedlex SPARQL, MediaWiki API, HTTP)
  parse.py             stage 2 — dispatch to parsers
  parsers/
    akn.py             Akoma Ntoso law parser (articles + annex figures)
    wikipedia.py       MediaWiki prose-section parser
    html_generic.py    generic prose-page parser (météo, cantonal)
  normalize.py         stage 3 — merge -> SQLite + asset localization
  schema.py            KnowledgeUnit + SQLite DDL + JSON export
  themes.py            exam taxonomy + tagging rules
data/                  generated (gitignored): raw/ cache, assets/, kb.sqlite, kb.json
```

## Phase 2 (not built — designed for)

The KB is queryable by theme so Phase 2 can balance question selection the way the
real exam does (60 questions, 50 min, 3 choices, max 15 wrong). Figures are stored
locally with captions so signal questions can render them.
