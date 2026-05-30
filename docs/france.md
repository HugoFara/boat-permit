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

Primary sources (`src/fr/sources_fr.py`):

| id | Source | Reference |
|----|--------|-----------|
| `arrete_2007` | Arrêté du 28 septembre 2007 (permis plaisance, référentiel) | JORFTEXT000000428843 |
| `decret_2007` | Décret n° 2007-1167 du 2 août 2007 | JORFTEXT000000648362 |
| `ripam` | RIPAM — Règlement international pour prévenir les abordages en mer (COLREG) | Légifrance / OMI |
| `rgp` | Règlement général de police de la navigation intérieure (RGP/RGPNI, CEVNI) | Code des transports R4241-1 s. |
| `division_240` | Division 240 — matériel de sécurité des navires de plaisance < 24 m | Arrêté / mer.gouv.fr |
| `iala_a` | Balisage maritime IALA région A | Référentiel / SHOM |

**Not ingested:** the operator exam banks (La Poste, Dekra, SGS, Bureau Veritas
have run the QCM under confidential public contract since June 2022) and any paid
prep app's questions.

## No official public question bank

Unlike some jurisdictions, France publishes **no** free official QCM bank. The
exam questions are operator-confidential. So — exactly as for Switzerland — the
tool **derives** its questions from the primary legal texts above, each with a
provenance citation, and ships them behind the same review gate.

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
