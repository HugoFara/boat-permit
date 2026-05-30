# Boat-permit — apprendre les règles de navigation à partir de sources vérifiées

**Langues :** [English](README.md) · **Français** · [Deutsch](README.de.md) · [Italiano](README.it.md)

Un cadre ouvert pour réviser les **examens théoriques nationaux du permis de
navigation**, construit **uniquement** à partir de textes de loi du domaine public et
de références dont la réutilisation est clairement autorisée. Il couvre aujourd'hui
trois pays — **🇫🇷 France · 🇩🇪 Allemagne · 🇨🇭 Suisse** — derrière un seul
pipeline et un seul player, et il est conçu pour qu'ajouter un pays revienne à créer
un seul nouveau fichier, et non à forker le projet.

Pour chaque pays, il fournit trois choses :

1. une **base de connaissances** (KB) structurée et versionnée, dérivée du droit de ce pays,
2. une **banque de questions d'entraînement sourcées**, et
3. un **player statique** sans dépendance (navigateur / GitHub Pages) avec des exports
   **Anki** et **Moodle GIFT**.

## La frontière juridique (tout l'enjeu)

Chaque examen officiel s'appuie sur une banque de questions, que les applications de
révision payantes reconditionnent. Ce projet **n'y touche délibérément pas du tout**.
La règle stricte, appliquée à l'identique dans chaque pays :

- **Il n'ingère** que des textes de loi et des références qui sont dans le domaine
  public ou qui portent une licence de réutilisation explicite. La provenance et une
  mention de licence sont conservées sur **chaque** unité et **chaque** question.
- **Il ne récupère, ne stocke et ne reproduit jamais** une banque de questions
  propriétaire ni les questions/explications d'une application payante.
- **Chaque question d'entraînement est dérivée de sources primaires** et porte une
  citation renvoyant à l'article, à la règle ou à la figure dont elle provient. Rédiger
  une question de mémoire est interdit — la source fait autorité.

Comment cette règle s'applique selon les pays :

| Pays | Base juridique (publique/réutilisable) | Base des questions |
|---------|-----------------------------|----------------|
| 🇫🇷 **France** | Légifrance / DILA LEGI sous **Licence Ouverte / Etalab** (les actes officiels français ne sont pas protégés par le droit d'auteur) | Dérivée du droit ingéré — les banques de QCM propriétaires des opérateurs (La Poste/Dekra/SGS/Bureau Veritas) ne sont **jamais** touchées |
| 🇩🇪 **Allemagne** | XML de gesetze-im-internet.de, domaine public au titre du **§5(1) UrhG** | Les *amtliche Fragenkataloge* officiels d'**ELWIS** sont réutilisables tels quels au titre du **§5(2) UrhG** (citer www.elwis.de, sans modification) — ingérés en l'état |
| 🇨🇭 **Suisse** | XML Akoma Ntoso de Fedlex, le droit fédéral suisse est dans le domaine public | Dérivée du droit — la banque sous licence asa reconditionnée par les applications payantes n'est **jamais** touchée |

## Démarrage rapide

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

Les builds de la KB sont mis en cache et ré-exécutables ; `--force` relance la
récupération. Les étapes question et web sont de pures transformations des sorties
précédentes.

## Comment ça marche

Le pipeline est le même pour chaque pays ; seul le descripteur propre à chaque pays change.

### Phase 1 — base de connaissances

Trois étapes ré-exécutables indépendamment, chacune lisant la sortie de la précédente :

| Étape | Commande | Ce qu'elle fait |
|-------|---------|--------------|
| **Fetch** | `run.py fetch [--country X]` | Récupère les sources brutes dans `data/raw/<id>/`, telles quelles, avec un `manifest.json` consignant l'URL + la date de récupération + la version juridique. Ne re-récupère jamais sauf avec `--force`. |
| **Parse** | `run.py parse [--country X]` | Transforme chaque source brute en `KnowledgeUnit`s structurées (pur, sans réseau). Un parser par type de source — Akoma Ntoso (CH), XML gii (DE), XML LEGI (FR), PDF COLREG (INT), MediaWiki/HTML. |
| **Normalize** | (partie de `build`) | Fusionne en une seule KB SQLite, localise les ressources images, relie articles ↔ figures, marque chaque unité avec le thème d'examen du pays concerné, et appose une version. |

Limitez à des sources spécifiques avec `--only`. Le droit de chaque pays (signaux,
balisage, feux, signaux sonores) porte les schémas sous forme de ressources images
localisées, légendées à partir des tableaux d'annexes et reliées aux articles qui les
citent.

### Phase 2 — banque de questions

| Étape | Commande | Ce qu'elle fait |
|------|---------|--------------|
| **Figures** | `run.py questions` | Génère de manière déterministe des questions de reconnaissance de figures à partir des schémas d'annexes légendés. Distracteurs issus d'ensembles de confusion indexés par type de signal ; amorcés par sha1, donc la sortie est stable. Auto-approuvées. |
| **Derive / draft** | `run.py draft …` · `run.py fr` | Rédige des questions strictement **à partir du texte source ingéré** (un garde-fou d'ancrage lexical élimine les hallucinations probables), chacune épinglée à une citation faisant autorité. Arrive au statut **`pending`**. |
| **Catalogue ingest** | `run.py questions --country DE` | Ingère un catalogue officiel réutilisable (l'ELWIS allemand) **mot pour mot**, chaque question étant taguée + portant son attribution §5. |
| **Review** | `run.py review --list / --approve / --reject` | Étape de relecture humaine (review gate). Seules les questions `auto_approved` + `approved` sont jamais exportées. |
| **Web** | `run.py web` | Ré-exporte chaque banque approuvée vers `questions.<lang>.json`, regroupe les ressources de figures dans `web/`, et écrit les **paquets Anki** par langue (`web/anki/`) + les fichiers **Moodle GIFT** (`web/gift/`). |

## Les pays

Les trois sont de premier rang : chacun correspond à un descripteur dans
`src/countries/` qui déclare ses sources juridiques, sa taxonomie de thèmes d'examen +
son tagueur, son catalogue de permis, ses règles d'examen et ses régimes régionaux — la
configuration que consomme le pipeline. Ajouter un pays revient à un seul nouveau
fichier + une ligne de registre (`src/countries/registry.py`), de sorte que les travaux
en parallèle n'entrent pas en collision.

### 🇫🇷 France — permis plaisance

Le **permis plaisance** en deux options : **côtière** (maritime, ≤6 NM d'un abri, de
jour comme de nuit) et **eaux intérieures** (fleuves, canaux, lacs). L'examen est
national — **40 QCM à réponse unique, réussite à ≤5 erreurs (35/40), ~30 min**,
identique partout (pas de variation régionale). La France est **seed- + law-derived** :
les questions sont rédigées **à partir** du droit français ingéré, jamais à partir des
banques propriétaires des opérateurs.

- **Droit (Licence Ouverte / Etalab) :** le projet ingère les données ouvertes en
  masse **DILA LEGI** — l'équivalent français de Fedlex — pour le **Code des
  transports, Partie 4** (le RGP, la transposition française de CEVNI), le **Code de
  l'environnement** (MARPOL/rejets), le **décret & arrêté du 28 sept. 2007** (le
  référentiel) et la **Division 245** (≈1 346 articles en vigueur). L'ancrage maritime
  que LEGI ne porte pas — **RIPAM/COLREG, balisage IALA Région A, SHOM** marées/datums —
  est ingéré comme un corpus de faits de référence vérifiés (les faits ne sont pas
  protégeables par le droit d'auteur ; chacun cité à sa source primaire).
- **Build :** `python run.py fr` → les deux banques d'options + les players `web/fr/`.

### 🇩🇪 Allemagne — Sportbootführerschein

Le **Sportbootführerschein** allemand, avec le catalogue le plus riche des trois.

- **Droit (§5(1) UrhG, domaine public) :** gesetze-im-internet.de sert chaque
  ordonnance sous forme de XML structuré à `<slug>/xml.zip`. `run.py build --country DE`
  récupère les **SeeSchStrO, BinSchStrO, le KVR/COLREG, la SpFV et la RheinSchPV** (≈1
  750 unités d'articles incluant les schémas de balisage/feux/signaux), tagués selon une
  taxonomie allemande (Verkehrsregeln, Schifffahrtszeichen, Lichter/Signale,
  Wetterkunde, …).
- **Catalogue officiel (§5(2) UrhG, réutilisable) :** contrairement à la banque suisse
  inaccessible, les *amtliche Fragenkataloge* d'**ELWIS** pour le SBF See/Binnen sont
  réutilisables *"solange der Inhalt unverändert bleibt und als Quelle www.elwis.de
  angegeben wird"*. `run.py questions --country DE` ingère les deux catalogues **mot
  pour mot** (≈515 questions après déduplication des Basisfragen communes), chacune
  taguée à un thème + un bloc d'examen avec l'attribution §5 dans sa provenance. Comme
  la réutilisation est conditionnée à *l'absence de modification*, la banque allemande
  est uniquement en allemand et les options sont seulement **réordonnées** pour
  l'affichage, jamais reformulées.
- **Permis & examen :** les **SBF See / SBF Binnen** fédéraux (moteur / voile / les
  deux), les **SKS / SSS / SHS** facultatifs, et le **Bodensee-Schifferpatent**
  trinational. La notation est **par bloc** (par ex. ≥5/7 Basis **et** ≥18/23
  spezifisch), dans `questions/schema.py:grade_exam_blocks`. Le balisage est **IALA
  Région A**. Une réforme 2025–26 est signalée comme *pending*, et non comme droit
  établi (`countries/de.py:REFORM_NOTE`).
- **Player :** le **🇩🇪 Deutschland** de la countrybar ouvre `web/de/`, où un sélecteur
  de permis pilote le véritable **examen structuré par blocs**.

### 🇨🇭 Suisse — bateau à moteur cat-A (+ ébauche cat-D)

L'examen théorique du **bateau à moteur catégorie A**, standardisé entre cantons par la
**VKS** (l'OCV genevois administre la norme nationale sur le Lac Léman).

- **Droit (domaine public) :** les pages Fedlex sont rendues en JS, donc le HTML de la
  page n'est jamais récupéré — le build résout le **XML Akoma Ntoso** (texte des
  articles) et ses images d'annexes via le **endpoint SPARQL** de Fedlex + le filestore.
  Sources : l'**ONI** (RS 747.201.1) et le **RNL** (Léman, RS 747.221.1), plus des
  références météo et de matelotage sous licence libre.
- **Examen :** **60 questions · 50 minutes · 180 points · réussite à 165/180.** Chaque
  question comporte 3 réponses dont **1 à 2 sont correctes** (multi-sélection), notées en
  **tout ou rien**. La seule variation par canton est la **limite de temps** (50 min
  GE/VD · 45 min Berne), modélisée dans `src/cantons.py` et exposée comme un **sélecteur
  de canton** dans le player.
- **Permis :** le **cat-A** est la cible entièrement ancrée à six thèmes (Définitions,
  Météorologie, Lois, Signalisation, Matelotage, Eaux frontalières). Le **cat-D**
  (voile) est ébauché — il partage le tronc commun du cat-A et ajoute un thème `voile`,
  en attente d'une source de technique de voile sous licence libre.
- **Build :** `python run.py build` + `python run.py questions` → `web/` (la valeur par
  défaut, donc un build nu correspond au build suisse).

## Codes harmonisés — la couche supranationale (`INT`)

Au-dessus des examens nationaux se trouvent les **codes de navigation harmonisés** que
partage la banque de chaque pays : **COLREGS** (règles maritimes d'abordage) et
**CEVNI** (le code européen des voies de navigation intérieure) — les racines de l'arbre
des régimes dans `src/jurisdictions.py`. Le membre de registre `INT`
(`src/countries/intl.py`) les ancre dans leur **texte canonique** plutôt que seulement
indirectement via les transpositions nationales. Il sert uniquement au sourcing — pas de
permis, pas de bundle player — donc il n'apparaît jamais dans le sélecteur de pays.

- **COLREG — ingéré.** Le Règlement international (1972) tel quel est une **œuvre du
  gouvernement des États-Unis** (domaine public, 17 USC §105) tel que publié par
  l'US Coast Guard. `run.py build --country INT` récupère le PDF "Navigation Rules" de
  l'USCG et le parser (`src/parsers/colreg.py`) ne conserve que ses pages
  *International*, en segmentant les 38 Règles + Annexes I–IV. L'édition consolidée et
  protégée de l'OMI n'est **pas** utilisée.
- **CEVNI — non ingéré (barrière de licence).** Le texte canonique de l'UNECE
  (Résolution n° 24, Rev.6) est sous tous droits réservés : la politique de l'ONU exige
  une autorisation écrite et interdit la redistribution/les dérivés, il échoue donc à la
  règle de réutilisation du projet. Il est enregistré comme une `Reference` ; une demande
  d'autorisation de reproduction a été envoyée à l'UNECE et est en attente. Tant qu'elle
  n'est pas accordée, la base CEVNI reste ancrée via les transpositions nationales pour
  les eaux intérieures, du domaine public, déjà ingérées.

### Tronc commun partagé vs banque nationale

Comme tant de contenu est harmonisé, chaque question est classée au moment du build
(`src/scope.py`) comme l'un de `universal` (matelotage/météo/premiers secours) · `cevni`
(code des eaux intérieures) · `colregs` (code maritime) · `national` (loi) · `local`
(un seul plan d'eau). Les bases portables sont mutualisées entre **toutes** les banques
des pays, par langue, dans des bundles additifs `web/questions.<base>.<lang>.json`, et le
basculement **National ⟷ Common-core** du player compose `universal + (cevni | colregs)`
pour la filière du permis actif. Les bundles nationaux restent **identiques au
byte près** d'un build à l'autre — un invariant suivi. Voir `docs/scope.md`.

## Le player

`web/` est du JavaScript vanilla sans dépendance. Il charge la banque de la langue
active, lit la configuration d'examen depuis son `meta`, et exécute un **examen**
chronométré et un mode **practice** avec corrections sourcées. Vous pouvez **réviser par
domaine** (choisir quels thèmes alimentent une session), basculer le pool
**National ⟷ Common-core**, et l'écran de résultats détaille le **score par domaine**.
La **countrybar 🇫🇷 / 🇩🇪 / 🇨🇭** bascule entre les players nationaux, chacun réutilisant
le même moteur avec ses propres règles d'examen. Le player propose aussi le **paquet
Anki** et le fichier **Moodle GIFT** pour la langue active en téléchargements en un clic.

### Langues

L'interface du player est traduite en **français, allemand, italien et anglais**, et le
contenu des questions est construit par langue. Lorsque le droit officiel d'un pays
n'est pas publié dans une langue (par ex. l'anglais nulle part, l'italien seulement en
CH), la banque est signalée **unofficial** ou se replie sur la langue opérante avec une
mention visible. Les chaînes d'interface se trouvent dans `web/i18n.js` ; `run.py web`
émet un `questions.<lang>.json` par langue plus un manifeste `languages.json`.

### Exports Anki & Moodle

| Outil | Commande | Ce qu'il fait |
|------|---------|--------------|
| **Anki** | `python tools/anki.py export [lang]` | Un véritable `.apkg` (zip + SQLite, figures incluses, un **sous-paquet par thème**) et un `.tsv` éditable. `import file.tsv --apply` réintègre les modifications comme brouillons **pending**. Bibliothèque standard uniquement. |
| **GIFT** | `python tools/gift.py export [lang]` | Un fichier **Moodle GIFT**, un `$CATEGORY` par thème, figures intégrées en URIs `data:` base64 pour qu'il soit autonome. Bibliothèque standard uniquement. |

Le mapping Anki est **sans perte pour le texte éditable** mais **verrouillé en
structure** : les options correctes, l'image et la provenance restent la propriété de la
banque, de sorte qu'une modification réimportée depuis Anki/TSV ne peut jamais inverser
silencieusement une réponse — elle arrive comme un brouillon `pending` pour
re-relecture. Tous les identifiants de paquet sont dérivés du contenu (sha1) et les
mtimes épinglés, donc un rebuild est identique au byte près.

## Organisation

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

Tout est hors ligne ; aucun réseau ni clé API n'est nécessaire.

## Licence

L'outillage de ce dépôt est ouvert à la réutilisation. Le contenu ingéré conserve sa
propre licence, consignée par unité et par question : le droit fédéral suisse/français
et le COLREG (USCG) sont dans le domaine public ; les données ouvertes françaises sont
sous Licence Ouverte / Etalab ; le droit allemand relève du §5(1) UrhG et le catalogue
ELWIS du §5(2) UrhG (citer www.elwis.de, sans modification) ; le matériel de matelotage
de Wikipédia est sous CC BY-SA 4.0 ; les pages météo/cantonales sont des sources
officielles utilisées avec attribution.
