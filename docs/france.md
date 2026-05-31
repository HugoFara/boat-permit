# France — *permis plaisance* (extension de l'outil de révision)

Ce document décrit l'extension France de l'outil de révision boating-licence. La limite
juridique et éditoriale est **la même que pour le cœur suisse** : chaque question est
*dérivée de sources primaires* et porte une citation renvoyant au texte dont elle est
issue. Nous ne récupérons, ne stockons ni ne reproduisons **aucune** banque d'examen
d'un opérateur.

## Types de permis

La France appelle le permis de conduite de loisir le **permis plaisance** (*permis de
conduire les bateaux de plaisance à moteur*). Il est requis pour un bateau à moteur
dont la puissance du moteur dépasse **4,5 kW (≈6 ch)**. Il comporte deux **options**
de base et deux **extensions** :

| Code | Permis | Autorise | Examen théorique |
|------|--------|-----------|-------------|
| `cotiere` | Option **côtière** | Navigation en mer jusqu'à **6 milles nautiques** d'un abri, de jour comme de nuit, quelle que soit la puissance du moteur | 40 QCM, ≤5 erreurs |
| `eaux_interieures` | Option **eaux intérieures** | Fleuves, canaux, lacs et voies navigables intérieures | 40 QCM, ≤5 erreurs |
| `hauturiere` | Extension **hauturière** | Hauturier, **sans limite de distance** (nécessite d'abord l'option côtière) | Théorie seulement — travail sur carte, marées, relèvements, route |
| `grande_plaisance` | Extension **grande plaisance eaux intérieures** | Bateaux fluviaux de **plus de 20 m** | Pratique seulement (pas de QCM) |

L'outil amorce les deux options de base (`cotiere`, `eaux_interieures`). Les deux
extensions sont enregistrées par souci d'exhaustivité ; l'hauturière repose sur des
exercices de carte (pas une banque de QCM) et la grande plaisance n'a pas d'examen
théorique.

## Structure de l'examen

Les deux options de base utilisent le **même** format (Arrêté du 28 septembre 2007, art. 1 &
art. 2) :

- **40** questions à choix multiple, une seule meilleure réponse.
- Réussite = **au plus 5 erreurs** (c.-à-d. **35/40**).
- ~30 minutes, répondu sur tablette.
- Un examen théorique réussi est valable **18 mois** pour passer l'épreuve pratique.

Dans le modèle de points de ce projet, cela donne `40 questions × 1 point = 40 au total, réussite à 35,
tout ou rien`. L'examen est **national** — il n'y a aucune variation cantonale/régionale
(contrairement à l'examen suisse VKS), donc le lecteur n'affiche pas de sélecteur de région pour la France.

## Domaines de connaissances (le *référentiel* officiel)

D'après les annexes de l'Arrêté du 28 septembre 2007. Regroupés ici dans les thèmes
d'examen sur lesquels l'outil s'équilibre (`src/fr/themes_fr.py`) :

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

## Sources juridiques & licences

Les **actes officiels** français (lois, décrets, *arrêtés*) sont exclus du droit
d'auteur, et le contenu de Légifrance / data.gouv.fr est publié sous la **Licence Ouverte /
Open Licence 2.0 (Etalab)** — réutilisation libre, commerciale et non commerciale, dans le monde entier,
avec attribution. C'est l'équivalent français de la base suisse relevant du domaine public.

Sources primaires (`src/fr/sources_fr.py`). Chaque question est ancrée dans l'une d'elles
et a été **vérifiée par rapport au texte réel** (2026-05-30), avec une référence précise
d'article/de règle — jamais paraphrasée de mémoire :

| id | Source | Référence |
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

**Non intégrées :** les banques d'examen des opérateurs (La Poste, Dekra, SGS, Bureau Veritas
font passer les QCM dans le cadre d'un marché public confidentiel depuis juin 2022) et les
questions de toute application de préparation payante.

## Pas de banque de questions publique officielle

Contrairement à certaines juridictions, la France ne publie **aucune** banque de QCM
officielle gratuite. Les questions d'examen sont confidentielles, propres aux opérateurs. Donc
— exactement comme pour la Suisse — l'outil **dérive** ses questions des textes juridiques primaires
ci-dessus, chacune avec une citation de provenance, et les livre derrière la même barrière de relecture.

## Droit intégré (Légifrance / DILA LEGI)

La France ancre sa banque dans la **loi réelle**, pas dans la mémoire. `src/fr/legi.py`
intègre, à partir des données ouvertes officielles **DILA LEGI** (le dump XML en masse
`Freemium_legi_global_*.tar.gz` — Licence Ouverte / Etalab, sans
identifiants d'API), chaque article en vigueur (`VIGUEUR`) des textes que la banque cite et
écrit des `KnowledgeUnit`s au niveau de l'article (réutilisant `src/schema.py`). Le dump contient
à la fois les **codes** consolidés et les **lois/décrets/arrêtés** non codifiés
(`TNC_en_vigueur/JORF`), de sorte qu'un seul téléchargement les couvre tous :

| `source_id` | texte | articles |
|---|---|---|
| `code_transports` | Code des transports, 4ᵉ partie (navigation intérieure = le RGP) | 1160 |
| `code_environnement` | Code de l'environnement, art. L.218-x (rejets des navires / MARPOL) | 90 |
| `decret_2007` | Décret n° 2007-1167 (permis plaisance) | 40 |
| `arrete_2007` | Arrêté du 28 sept. 2007 (référentiel) | 37 |
| `division_245` | Arrêté du 10 fév. 2016 (Division 245 — eaux intérieures) | 19 |

```bash
python -m src.fr.legi extract   # data/raw/legi/legi_global.tar.gz → article trees
python -m src.fr.legi build     # → data/kb.fr.sqlite + src/fr/legi_kb.json (1346 arts)
python -m src.fr.legi verify    # cross-check every seed citation vs the ingested law
```

Le corpus durable est **committé** dans `src/fr/legi_kb.json` (droit relevant du domaine public),
de sorte que la KB se reconstruit et que la vérification s'exécute **sans** le dump de 1,2 Go (qui
reste sous `data/raw/`, ignoré par git). `tests/test_legi.py` affirme que chaque
article que l'amorce cite *dans un texte intégré* existe dans la loi — de sorte qu'une citation
ne peut pas dériver silencieusement de la source. Cela a déjà détecté une erreur : `A.4241-48-12`
(feux des navires à voile) → `A.4241-48-13` (feux des menues embarcations à moteur). Chaque unité
porte une URL Légifrance profonde par article et la date d'entrée en vigueur.

## Corpus de référence intégré (IALA + SHOM)

Le contenu **côtière** repose sur des sources que LEGI ne contient pas : le **système** de
balisage maritime **IALA** (région A) et les marées/cartes **SHOM**. Ceux-ci ne sont *pas* sous licence ouverte
permettant la rediffusion verbatim (IALA R1001 est © IALA ; les ouvrages SHOM portent les conditions SHOM —
ses *données* ouvertes sont sous Licence Ouverte). Ce qui est librement utilisable, c'est le **contenu factuel**
(la couleur/forme/voyant/feu d'une marque ; le zéro hydrographique ; la plage de coefficient) — non
protégeable par le droit d'auteur. Donc `src/fr/reference_fr.py` intègre ces faits, chacun **vérifié
par rapport à et cité vers la source primaire** (lu dans les Tables 1–9 d'IALA R1001 Éd.2.0 et
la fiche SHOM *Prédiction de marée*), en tant que `KnowledgeUnit`s — **et non de la prose copiée** :

| `source_id` | faits | thèmes |
|---|---|---|
| `iala_a` | 10 — marques latérales / de chenal préféré / 4 cardinales / de danger isolé / d'eaux saines / spéciales (région A : couleur, forme, voyant, feu) | `balisage` |
| `shom` | 9 — zéro hydrographique, marnage, coefficient (20–120), vives/mortes-eaux, flot/jusant, cycle semi-diurne, niveaux caractéristiques, règle des douzièmes, étale | `meteo_maree` |

```bash
python -m src.fr.reference_fr build   # → src/fr/reference_kb.json + data/kb.fr.sqlite
```

Committé dans `src/fr/reference_kb.json` ; `tests/test_reference.py` fige la structure et
les faits porteurs (couleurs latérales de la région A, la plage de coefficient 20–120, la
définition du zéro hydrographique). Cela ancre la dérivation future des questions **côtière** de la même façon que
`legi_kb.json` ancre celle des eaux intérieures.

*Encore vérifié hors bande* (pas d'intégration) : COLREG/RIPAM (intégré via la couche `INT`),
CEVNI (UNECE), Règlement des radiocommunications de l'UIT, la Directive UE 2013/53, les *arrêtés des
préfets maritimes*, et la Division 240 (tables annexées pas proprement dans LEGI).

## Portée des questions & le pool de tronc commun

La France participe à la couche **scope** partagée (`src/scope.py`, voir
[`scope.md`](scope.md)). Chaque question française est classée dans un échelon de
l'arbre des régimes :

| option | base (tronc portable) | surcouche (France uniquement) |
|---|---|---|
| côtière | `colregs` (règles RIPAM, balisage IALA-A, feux en mer) + `universal` (météo/marées, environnement, sécurité générique) | `national` (loi du permis & de la radio, kit Division-240) |
| eaux intérieures | `cevni` (code fluvial RGP, écluses, signes fluviaux) + `universal` | `national` |

`build_fr.py` émet le sous-ensemble portable sous forme de sous-bundles par base
(`web/fr/<option>/questions.<base>.<lang>.json`) et les liste dans le bloc `core`
du manifeste de l'option, de sorte que chaque lecteur propose une bascule **National ⟷ Tronc commun** :
la banque nationale correspond à toute la portée de l'examen à 40 questions ; le tronc commun n'entraîne que
les règles portables d'un pays à l'autre (30 côtière = universal 10 + colregs 20 ; 34 eaux
intérieures = universal 8 + cevni 26). La France est pilotée par amorce, donc son tronc est
*local à la France* (il n'est pas encore fusionné dans le tronc global CH/DE) — voir `scope.md`
› *Seed-driven countries*.

## Build

```bash
python run.py fr            # build both France option banks + bundle web/fr/
python -m http.server -d web 8000   # http://localhost:8000/fr/
```

Voir `src/countries/fr.py` (descripteur du registre des pays), `src/fr/` (contenu
France + `build_fr.py`), et `src/scope.py` (la branche du classifieur France).
