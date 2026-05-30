# France — *permis plaisance* (extension of the study tool)

This documents the France extension of the boat-permit study tool. The legal and
editorial boundary is the **same as the Swiss core**: every question is *derived
from primary sources* and carries a citation back to the text it came from. We do
**not** scrape, store, or reproduce any operator's exam bank.

## Permit types

France calls the recreational driving licence the **permis plaisance** (*permis de
conduire les bateaux de plaisance à moteur*). It is required for a motor boat
whose engine power exceeds **4,5 kW (≈6 ch)**. It has two base **options** and two
**extensions**:

| Code | Permit | Authorises | Theory exam |
|------|--------|-----------|-------------|
| `cotiere` | Option **côtière** | Sea navigation up to **6 milles nautiques** from a shelter, day and night, any engine power | 40 QCM, ≤5 errors |
| `eaux_interieures` | Option **eaux intérieures** | Rivers, canals, lakes and inland waterways | 40 QCM, ≤5 errors |
| `hauturiere` | Extension **hauturière** | Offshore, **no distance limit** (requires the côtière option first) | Theory only — chart work, tides, bearings, route |
| `grande_plaisance` | Extension **grande plaisance eaux intérieures** | Inland boats **over 20 m** | Practical only (no QCM) |

The tool seeds the two base options (`cotiere`, `eaux_interieures`). The two
extensions are registered for completeness; the hauturière is chart-exercise based
(not a QCM bank) and grande plaisance has no theory exam.

## Exam structure

Both base options use the **same** format (Arrêté du 28 septembre 2007, art. 1 &
art. 2):

- **40** multiple-choice questions, single best answer.
- Pass = **at most 5 errors** (i.e. **35/40**).
- ~30 minutes, answered on a tablet.
- A passed theory exam is valid **18 months** to take the practical.

In this project's point model that is `40 questions × 1 point = 40 total, pass 35,
all-or-nothing`. The exam is **national** — there is no cantonal/regional variance
(unlike the Swiss VKS exam), so the player shows no region picker for France.

## Knowledge domains (the official *référentiel*)

From the annexes of the Arrêté du 28 septembre 2007. Grouped here into the exam
themes the tool balances on (`src/fr/themes_fr.py`):

**Option côtière**
- `securite` — sécurité, matériel d'armement (Division 240), catégories de conception, limites d'embarquement
- `balisage` — balisage et signalisation maritime (système **IALA région A**), marques de plage, pictogrammes
- `regles_route` — règles de barre et de route (**RIPAM** / COLREG)
- `feux_signaux` — feux et marques des navires ; signaux sonores, de détresse, portuaires, de visibilité réduite
- `meteo_maree` — météorologie, marées, lecture de carte
- `reglementation` — réglementation du permis, **VHF/radio**, ski nautique, responsabilité du chef de bord
- `environnement` — protection de l'environnement (rejets, peintures, ressource halieutique)

**Option eaux intérieures**
- `voies_navigables` — caractéristiques des voies, terminologie, stationnement
- `ecluses` — écluses et barrages (gardés, automatiques, manuels) et sécurité
- `signalisation_fluviale` — signalisation des voies et des bateaux (**RGP**, aligné **CEVNI**)
- `regles_route` — règles de route et de priorité (partagé)
- `securite` — matériel, marques d'identification, menues embarcations (partagé)
- `reglementation` — police de la navigation, permis, VHF fluviale (partagé)
- `environnement` — protection de l'environnement (partagé)

## Legal sources & licensing

French **official acts** (laws, decrees, *arrêtés*) are excluded from copyright,
and Légifrance / data.gouv.fr content is published under the **Licence Ouverte /
Open Licence 2.0 (Etalab)** — free reuse, commercial and non-commercial, worldwide,
with attribution. This is the France analogue of the Swiss public-domain basis.

Primary sources (`src/fr/sources_fr.py`). Every question is grounded in one of these
and was **verified against the actual text** (2026-05-30), with a precise
article/rule reference — never paraphrased from memory:

| id | Source | Reference |
|----|--------|-----------|
| `ripam` | RIPAM / COLREG — abordages en mer (incl. annexe IV, signaux de détresse) | Légifrance JORFTEXT000000305722 / OMI |
| `rgp` | Règlement général de police de la navigation intérieure | Code des transports, art. A.4241-x |
| `cevni` | CEVNI — Code européen des voies de navigation intérieure | CEE-ONU, Résolution n° 24 |
| `decret_2007` | Décret n° 2007-1167 du 2 août 2007 (permis : portée, puissance, âge) | JORFTEXT000000648362 |
| `arrete_2007` | Arrêté du 28 septembre 2007 (référentiel) | JORFTEXT000000428843 |
| `division_240` | Division 240 — armement/sécurité, navires de plaisance de mer < 24 m | Arrêté / mer.gouv.fr |
| `division_245` | Division 245 (arrêté du 10 fév. 2016) — armement/sécurité eaux intérieures | JORFTEXT000032036538 |
| `directive_2013_53` | Directive 2013/53/UE — catégories de conception (A/B/C/D) | EUR-Lex CELEX 32013L0053 |
| `iala_a` | IALA — Système de balisage maritime, région A | Recommandation R1001 |
| `shom` | SHOM — marées et cartes (zéro hydrographique, marnage, coefficient, étale) | shom.fr |
| `meteo_france` | Météo-France / OMM — échelle de Beaufort (0–12) | meteofrance.com |
| `itu_rr` | UIT — Règlement des radiocommunications (VHF ch.16, MAYDAY/PAN PAN, CRR) | App. 18, art. 32/33/47 |
| `code_environnement` | Code de l'environnement / MARPOL — rejets en mer | art. L.218-11 s. |
| `code_transports` | Code des transports — alcoolémie, titre de navigation, RPP | art. L.4274-14, L.4221-1 |
| `prefet_maritime` | Arrêtés des préfets maritimes — bande des 300 m ; mouillage/posidonie | PREMAR Méditerranée |

**Not ingested:** the operator exam banks (La Poste, Dekra, SGS, Bureau Veritas
have run the QCM under confidential public contract since June 2022) and any paid
prep app's questions.

## No official public question bank

Unlike some jurisdictions, France publishes **no** free official QCM bank. The
exam questions are operator-confidential. So — exactly as for Switzerland — the
tool **derives** its questions from the primary legal texts above, each with a
provenance citation, and ships them behind the same review gate.

## Ingested law (Légifrance / DILA LEGI)

France grounds its bank in the **actual statute**, not recall. `src/fr/legi.py`
ingests the **Code des transports — 4ᵉ partie (navigation intérieure & transport
fluvial)**, i.e. the RGP and the titre-de-navigation/sanctions regime, from the
official **DILA LEGI** open data (the bulk `Freemium_legi_global_*.tar.gz` XML
dump, Licence Ouverte / Etalab — no API credentials). It keeps every in-force
(`VIGUEUR`) Part-4 article, tags it to a France theme, and writes article-level
`KnowledgeUnit`s (reusing `src/schema.py`).

```bash
python -m src.fr.legi extract   # data/raw/legi/legi_global.tar.gz → article tree
python -m src.fr.legi build     # → data/kb.fr.sqlite + src/fr/legi_kb.json (1160 arts)
python -m src.fr.legi verify    # cross-check every seed citation vs the ingested law
```

The durable corpus is **committed** at `src/fr/legi_kb.json` (≈1.6 MB, public-domain
law), so the KB rebuilds and the verification runs **without** the 1.2 GB dump (which
stays under `data/raw/`, git-ignored). `tests/test_legi.py` asserts every
Code-des-transports article the seed cites exists in the ingested law — so a
citation can't silently drift from the source. This already caught one error:
`A.4241-48-12` (sailing-vessel lights) → `A.4241-48-13` (motorised small-craft
lights). Each unit carries a deep per-article Légifrance URL
(`/codes/article_lc/<LEGIARTI>`) and the in-force date.

*Not yet ingested:* the Code de l'environnement (rejets) and the LODA texts (Décret
2007-1167, Arrêté du 28 sept 2007, Divisions 240/245) live in separate DILA
datasets; COLREG is ingested elsewhere via the `INT` universal-source layer. These
are the natural next ingestion targets.

## Question scope & the common-core pool

France participates in the shared **scope** layer (`src/scope.py`, see
[`scope.md`](scope.md)). Every French question is classified into one rung of the
regime tree:

| option | base (portable core) | overlay (France-only) |
|---|---|---|
| côtière | `colregs` (RIPAM rules, IALA-A buoyage, sea lights) + `universal` (météo/marées, environnement, generic safety) | `national` (permis & radio statute, Division-240 kit) |
| eaux intérieures | `cevni` (RGP inland code, locks, inland signs) + `universal` | `national` |

`build_fr.py` emits the portable subset as per-base sub-bundles
(`web/fr/<option>/questions.<base>.<lang>.json`) and lists them in the option
manifest's `core` block, so each player offers a **National ⟷ Common core** toggle:
the national bank is the full 40-question exam scope; the common core drills only
the cross-country-portable rules (30 côtière = universal 10 + colregs 20; 34 eaux
intérieures = universal 8 + cevni 26). France is seed-driven, so its core is
*France-local* (it is not yet merged into the global CH/DE core) — see `scope.md`
› *Seed-driven countries*.

## Build

```bash
python run.py fr            # build both France option banks + bundle web/fr/
python -m http.server -d web 8000   # http://localhost:8000/fr/
```

See `src/countries/fr.py` (country registry descriptor), `src/fr/` (France
content + `build_fr.py`), and `src/scope.py` (the France classifier branch).
