# Suisse — permis cat-A motorboat (cœur d'origine de l'outil)

Ce document décrit le cœur **suisse** de l'outil de révision boating-licence — la portée
d'origine du projet, dont les autres pays sont des extensions. La limite juridique et
éditoriale est la **règle de référence** de tout le projet : chaque question est
*dérivée de sources primaires* (le droit public) et porte une citation renvoyant à
l'article ou à la figure dont elle est issue. Nous ne récupérons, ne stockons ni ne
reproduisons **jamais** la banque asa sous licence repackagée par les applications de
préparation payantes.

> La Suisse est plurilingue : le droit est publié sur Fedlex en **français, allemand
> et italien**, et l'outil construit le contenu dans ces trois langues officielles
> (plus l'anglais, non officiel). Cette documentation pays est rédigée en français, la
> langue opérationnelle de l'examen visé (Léman / Genève).

## Types de permis

La Suisse fait passer **un seul examen théorique** pour toutes les catégories de
plaisance : le candidat cat-A (moteur) et le candidat cat-D (voile) composent le
*même* sujet. Ce qui distingue réellement les catégories, c'est le **seuil** qui rend
le permis obligatoire et une **épreuve pratique distincte**, et non la théorie.
Modélisés dans `src/questions/schema.py` (`PROFILES`) et `src/themes.py`
(`PERMIS_THEMES`) :

| Code | Permis | Seuil d'obligation | Contenu théorique |
|------|--------|--------------------|-------------------|
| `A` | Permis catégorie A — bateau à moteur | moteur > 6 kW (4,4 kW sur le lac de Constance) | les six thèmes étayés |
| `D` | Permis catégorie D — voile | surface vélique > 15 m² (12 m² sur le lac de Constance) | **théorie identique à la cat-A** + thème `voile` (étude, optionnel) |

Le lecteur web expose les deux catégories via un **sélecteur de permis** (à côté du
sélecteur de canton) : `run.py:_build_ch_web` émet le tableau `permits` dans
`web/ch/languages.json` (clés `code`/`drive`/`track`/`note`…), et les libellés/notes
sont localisés côté lecteur par code (`permit_<code>` / `permitNote_<code>` dans
`web/i18n.js`, fr/de/it/en). Comme la théorie est commune, choisir cat-A ou cat-D
**ne change pas** le pool de questions aujourd'hui ; le sélecteur affiche la catégorie
ciblée et son seuil. Le pool ne divergera qu'une fois le thème `voile` alimenté.

La technique de voile n'étant pas du texte d'ordonnance, le thème `voile` est
**alimenté par Wikipédia** (CC BY-SA, attribution requise) via des sources dédiées
`voile_wp` / `_de` / `_it` (`src/sources.py`) : allures, virement de bord, empannage,
louvoyage, gréement, foc, spinnaker, chavirage/dessalage. Les questions sont
**rédigées à partir du texte de ces unités** (jamais de mémoire) puis passées par la
barrière de relecture — voir `src/questions/seed_prose.py` et `data/seed_review.json`.

`voile` est un thème **PIN-ONLY et hors examen** :

- **pin-only** : il n'est tagué que sur les sources `voile_wp` (`pin_theme="voile"`).
  Il n'existe **aucune** règle de mots-clés pour `voile`, car le vocabulaire de voile
  apparaît aussi dans le *droit* (ONI art. 79 définit la cat-D par « surface vélique
  > 15 m² », art. 134/137/153 mentionnent gréement/gîte) — une règle de tag volerait
  ces articles à `lois`. C'est le sens du garde-fou dans `tests/test_voile.py`.
- **hors examen** : `voile` est dans `EXTENSION_THEMES`. Le lecteur le présente comme
  un **domaine d'étude pour la cat-D uniquement** (marqué ✦), l'exclut du tirage en
  *mode examen* (il n'est pas au sujet théorique, identique A/D) et ne l'affiche pas
  du tout pour la cat-A. Le manifeste porte `permits[].themes` + `extension_themes`
  pour piloter ce filtrage côté lecteur.

Contenu actuel : questions de voile rédigées en **français** (les sources DE/IT sont
ingérées pour permettre une rédaction ultérieure dans ces langues).

## Structure de l'examen

**60 questions · 50 minutes · 180 points · réussite à 165/180** (au plus 15 points de
faute, ≈ 5 questions entièrement fausses). Chaque question a 3 réponses dont **1 à 2
sont correctes** (choix multiple), notées **tout ou rien** par question (3 points
seulement si l'ensemble sélectionné correspond exactement).

L'examen est **standardisé entre cantons par la VKS** (Vereinigung der kantonalen
Schifffahrtsämter) : le nombre, les points, le seuil de réussite et le *contenu* sont
le standard national. L'OCV de Genève administre ce standard.

### Variance cantonale (la seule : le temps imparti)

Parce que la VKS standardise tout le reste nationalement, la *seule* chose qu'un canton
fait varier est le **temps imparti**. C'est modélisé dans `src/cantons.py` (la source
de vérité unique), exporté dans `languages.json`, et exposé comme **sélecteur de
canton** dans le lecteur pour que le minuteur corresponde au canton de l'apprenant :

| Canton | Temps | Léman ? | Note |
|--------|-------|---------|------|
| `GE` Genève | 50 min | oui | OCV — Office cantonal des véhicules ; standard VKS |
| `VD` Vaud | 50 min | oui | standard VKS |
| `BE` Berne | 45 min | non | variante documentée à 45 min de l'examen VKS |

La rive suisse du Léman n'est bordée que par **Genève et Vaud**. Seules les valeurs
vérifiées sont encodées ; tout ce qui n'est pas confirmé hérite du standard VKS de
**50 minutes** (`VKS_TIME_LIMIT_MIN`) — le défaut honnête, pas une supposition
déguisée en fait cantonal. La portée primaire du projet est Genève / OCV sur le Léman
(`DEFAULT_CANTON = "GE"`).

## Thèmes d'examen (cible de normalisation)

Les **six** thèmes cat-A (`src/themes.py`) :

1. `definitions` — Définitions
2. `meteorologie` — Météorologie
3. `lois` — Lois sur la navigation en eaux intérieures
4. `signalisation` — Signalisation et signaux acoustiques
5. `matelotage` — Matelotage
6. `eaux_frontalieres` — Eaux frontalières

(+ `voile` — Navigation à voile, pour la cat-D amorcée.) Le tag est basé sur des règles
et auditable (défaut de la source + heuristiques par mots-clés sur `ref`/`title`/`text`).

## Sources juridiques & licences

Le droit fédéral et cantonal suisse relève du **domaine public** (URG/LDA art. 5) et
est librement réutilisable. Les pages Fedlex sont rendues en JavaScript, donc le HTML
de la page n'est **jamais** récupéré : le build résout l'**XML Akoma Ntoso** (texte des
articles) et ses images d'annexe via l'**endpoint SPARQL** de Fedlex + le filestore.
Les images XML portent les diagrammes de signalisation (feux, bouées, panneaux),
légendés depuis les tables d'annexe et liés aux articles citants.

| id | Source | Thèmes | Licence |
|----|--------|--------|---------|
| `oni` | ONI — Ordonnance sur la navigation intérieure (RS 747.201.1) | Définitions, Lois, Signalisation (+ figures d'annexe) | domaine public |
| `rnl` | Règlement de la navigation sur le Léman (RS 747.221.1) | Eaux frontalières, Signalisation | domaine public |
| `matelotage_wp` | Wikipédia — nœuds marins | Matelotage | CC BY-SA 4.0 |
| `meteo_vents` | MétéoSuisse — Les vents du Léman | Météorologie | officiel, attribuer |
| `meteo_signaux` | SISL — signaux d'avis de tempête | Météorologie / Signalisation | vérification croisée |
| `geneve` | Genève — consignes générales de navigation | Lois (cantonal) | officiel, attribuer |

**Non intégrées :** la banque de ~520 questions sous licence asa (repackagée par
BoatDriver, iTheorie, theorie-bateau, …) et les questions/explications de toute
application payante. Comme aucune banque officielle gratuite n'existe, l'outil
**dérive** ses questions des textes primaires ci-dessus, chacune avec une citation de
provenance, derrière la barrière de relecture.

## Langues

L'examen est proposé dans les langues officielles suisses ; l'interface du lecteur est
traduite en **français, allemand, italien et anglais**, et le contenu des questions est
construit par langue (même pipeline de récupération, ELI différent par langue). Les PNG
des figures sont neutres ; seules les légendes se re-récupèrent par langue. Le lecteur
charge la banque de la langue active et **se rabat sur le français** (avec un avis
visible) pour toute langue dont la banque n'est pas encore construite. Le contenu
anglais, lorsqu'il est présent, est marqué **non officiel** — seules les versions
FR/DE/IT font foi (le droit suisse n'est pas publié en anglais).

## Portée des questions & le tronc commun

La Suisse participe à la couche **scope** partagée (`src/scope.py`, voir
[`scope.md`](scope.md)). La banque CH étant *eaux intérieures*, ses questions se classent
en `universal` (matelotage/météo/premiers secours), `cevni` (code fluvial), `national`
(statut) ou `local` (un plan d'eau, p. ex. les signaux de tempête du Léman). Les bases
portables (`universal` + `cevni`) sont mises en commun avec les autres banques par
langue, et le lecteur propose une bascule **National ⟷ Tronc commun**. Les bundles
nationaux restent **identiques au octet près** d'un build à l'autre — un invariant suivi.

## Build

```bash
python run.py build        # récupérer + parser + normaliser le droit → data/kb.sqlite
python run.py questions    # dériver les questions figures + amorces → data/questions.sqlite
python run.py web          # bundler la banque approuvée + assets → web/
python -m http.server -d web 8000   # http://localhost:8000
```

La Suisse est le pays par défaut (`DEFAULT = "CH"`), donc un build nu **est** le build
suisse — `--country` n'est pas nécessaire. Voir `src/countries/ch.py` (adaptateur fin
qui réutilise `src/sources.py`, `src/themes.py`, `src/cantons.py` et les profils cat-A/D
de `src/questions/schema.py`), et `src/scope.py` (le classifieur partagé).
