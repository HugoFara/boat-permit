"""Hand-authored seed question bank for the French *permis plaisance*.

Every entry is grounded in a primary authoritative source and carries it inline,
with a precise article/rule reference (verified 2026-05-30 against the actual
texts, not paraphrased from memory): RIPAM/COLREG, the RGP (Code des
transports A.4241-x) and CEVNI for inland, the Décret 2007-1167 and Arrêté du 28
sept. 2007 for the permit, Division 240/245 for safety equipment, the EU Directive
2013/53/UE for design categories, the IALA R1001 buoyage system, SHOM for
tides/charts, the ITU Radio Regulations for VHF, the Code de l'environnement /
MARPOL and the arrêtés des préfets maritimes. Most are French official acts or
public references freely reusable under the Licence Ouverte / Etalab; international
standards (IALA/ITU/MARPOL/Beaufort) are cited for their factual content. Nothing
is copied from an operator's exam bank; each item is freshly worded from the rule
it tests, and the exact source id lives in `sources_fr.FR_SOURCES`.

Shape — one self-contained dict per question (no external KB lookup, unlike the
Swiss seed):

    option   : "cotiere" | "eaux_interieures"   (which permit exam it belongs to)
    theme    : one of themes_fr.FR_THEMES
    source   : an id in sources_fr.FR_SOURCES (provenance)
    ref      : human reference string (e.g. "RIPAM règle 14")
    polarity : "affirmative" | "negative"
    fr / en  : {stem, explanation}  — FR is authoritative, EN an unofficial study aid
    choices  : [{fr, en, correct}]  — 3 options, exactly one correct; fr/en aligned
                                       by index so correctness can't drift

The French exam is single-best-answer, so every item has exactly one correct
choice. `build_fr.py` turns these into the canonical Question schema.
"""

from __future__ import annotations

SEED: list[dict] = [

    # ============================ OPTION CÔTIÈRE ============================

    # --- Balisage (IALA région A) ------------------------------------------
    {"option": "cotiere", "theme": "balisage", "source": "iala_a",
     "ref": "Balisage IALA région A — marques latérales", "polarity": "affirmative",
     "fr": {"stem": "En venant du large (système IALA région A), de quelle couleur "
            "et de quelle forme est une marque latérale de BÂBORD ?",
            "explanation": "IALA région A : la marque latérale bâbord est rouge et "
            "de forme cylindrique (« boîte ») ; on la laisse sur sa gauche en entrant."},
     "en": {"stem": "Coming from seaward (IALA region A), what colour and shape is a "
            "PORT-hand lateral mark?",
            "explanation": "IALA region A: the port mark is red and can-shaped; "
            "keep it on your left when entering."},
     "choices": [
         {"fr": "Rouge, cylindrique", "en": "Red, can-shaped", "correct": True},
         {"fr": "Verte, conique", "en": "Green, conical", "correct": False},
         {"fr": "Jaune, sphérique", "en": "Yellow, spherical", "correct": False}]},

    {"option": "cotiere", "theme": "balisage", "source": "iala_a",
     "ref": "Balisage IALA région A — marques latérales", "polarity": "affirmative",
     "fr": {"stem": "En venant du large (région A), de quelle couleur et de quelle "
            "forme est une marque latérale de TRIBORD ?",
            "explanation": "IALA région A : la marque latérale tribord est verte et "
            "de forme conique ; on la laisse sur sa droite en entrant."},
     "en": {"stem": "Coming from seaward (region A), what colour and shape is a "
            "STARBOARD-hand lateral mark?",
            "explanation": "IALA region A: the starboard mark is green and conical; "
            "keep it on your right when entering."},
     "choices": [
         {"fr": "Verte, conique", "en": "Green, conical", "correct": True},
         {"fr": "Rouge, cylindrique", "en": "Red, can-shaped", "correct": False},
         {"fr": "Noire et rouge, à sphères", "en": "Black and red, with spheres",
          "correct": False}]},

    {"option": "cotiere", "theme": "balisage", "source": "iala_a",
     "ref": "Balisage IALA — marque cardinale Nord", "polarity": "affirmative",
     "fr": {"stem": "Comment reconnaît-on le voyant d'une marque cardinale NORD, "
            "et de quel côté faut-il passer ?",
            "explanation": "Cardinale Nord : deux cônes noirs superposés, pointes "
            "vers le HAUT ; les eaux saines sont au nord, on passe donc au nord de "
            "la marque."},
     "en": {"stem": "How is a NORTH cardinal mark's topmark recognised, and which "
            "side do you pass?",
            "explanation": "North cardinal: two black cones, points UP; safe water "
            "is to the north, so pass to the north of the mark."},
     "choices": [
         {"fr": "Deux cônes pointes vers le haut ; on passe au nord", "en": "Two "
          "cones pointing up; pass to the north", "correct": True},
         {"fr": "Deux cônes pointes vers le bas ; on passe au sud", "en": "Two cones "
          "pointing down; pass to the south", "correct": False},
         {"fr": "Deux cônes pointes opposées ; on passe à l'ouest", "en": "Two cones "
          "point-to-point; pass to the west", "correct": False}]},

    {"option": "cotiere", "theme": "balisage", "source": "iala_a",
     "ref": "Balisage IALA — marque de danger isolé", "polarity": "affirmative",
     "fr": {"stem": "Que signale une marque à corps noir avec des bandes rouges "
            "horizontales, surmontée de deux sphères noires superposées ?",
            "explanation": "C'est la marque de danger isolé : elle est mouillée SUR "
            "un danger de faible étendue entouré d'eaux saines ; feu blanc à 2 éclats."},
     "en": {"stem": "What does a black mark with red horizontal bands, topped by two "
            "black spheres, indicate?",
            "explanation": "It is an isolated-danger mark: moored ON a small danger "
            "surrounded by safe water; white light, group flashing (2)."},
     "choices": [
         {"fr": "Un danger isolé entouré d'eaux saines", "en": "An isolated danger "
          "surrounded by safe water", "correct": True},
         {"fr": "L'entrée principale d'un port", "en": "The main harbour entrance",
          "correct": False},
         {"fr": "Une zone de baignade surveillée", "en": "A supervised swimming area",
          "correct": False}]},

    {"option": "cotiere", "theme": "balisage", "source": "iala_a",
     "ref": "Balisage IALA — marque d'eaux saines", "polarity": "affirmative",
     "fr": {"stem": "Que signale une marque à bandes verticales rouges et blanches, "
            "avec un voyant sphérique rouge ?",
            "explanation": "Marque d'eaux saines (milieu de chenal / atterrissage) : "
            "on peut la contourner indifféremment des deux côtés."},
     "en": {"stem": "What does a mark with red and white vertical stripes and a red "
            "spherical topmark indicate?",
            "explanation": "Safe-water mark (mid-channel / landfall): you may pass it "
            "on either side."},
     "choices": [
         {"fr": "Des eaux saines tout autour ; on passe de chaque côté", "en": "Safe "
          "water all around; pass on either side", "correct": True},
         {"fr": "Un danger isolé à contourner", "en": "An isolated danger to avoid",
          "correct": False},
         {"fr": "Le côté tribord d'un chenal", "en": "The starboard side of a channel",
          "correct": False}]},

    # --- Règles de barre et de route (RIPAM) -------------------------------
    {"option": "cotiere", "theme": "regles_route", "source": "ripam",
     "ref": "RIPAM règle 14 — Navires faisant des routes opposées",
     "polarity": "affirmative",
     "fr": {"stem": "Deux navires à moteur font des routes directement opposées "
            "(face à face) avec risque d'abordage. Que doit faire chacun d'eux ?",
            "explanation": "RIPAM règle 14 : chacun vient sur TRIBORD pour passer "
            "bâbord sur bâbord."},
     "en": {"stem": "Two power-driven vessels meet on directly opposite (head-on) "
            "courses with risk of collision. What must each do?",
            "explanation": "COLREG rule 14: each alters course to STARBOARD so they "
            "pass port to port."},
     "choices": [
         {"fr": "Chacun vient sur tribord", "en": "Each alters to starboard",
          "correct": True},
         {"fr": "Chacun vient sur bâbord", "en": "Each alters to port", "correct": False},
         {"fr": "Le plus rapide s'écarte, l'autre garde son cap", "en": "The faster "
          "one keeps clear, the other holds course", "correct": False}]},

    {"option": "cotiere", "theme": "regles_route", "source": "ripam",
     "ref": "RIPAM règle 15 — Routes qui se croisent", "polarity": "affirmative",
     "fr": {"stem": "Deux navires à moteur suivent des routes qui se croisent avec "
            "risque d'abordage. Lequel doit s'écarter ?",
            "explanation": "RIPAM règle 15 : le navire qui voit l'autre sur SON "
            "tribord doit s'en écarter ; l'autre (le privilégié) maintient cap et vitesse."},
     "en": {"stem": "Two power-driven vessels are on crossing courses with risk of "
            "collision. Which one must keep out of the way?",
            "explanation": "COLREG rule 15: the vessel that has the other on its OWN "
            "starboard side gives way; the other (stand-on) keeps course and speed."},
     "choices": [
         {"fr": "Celui qui a l'autre sur son tribord", "en": "The one that has the "
          "other on its starboard side", "correct": True},
         {"fr": "Celui qui a l'autre sur son bâbord", "en": "The one that has the "
          "other on its port side", "correct": False},
         {"fr": "Le plus grand des deux navires", "en": "The larger of the two vessels",
          "correct": False}]},

    {"option": "cotiere", "theme": "regles_route", "source": "ripam",
     "ref": "RIPAM règle 13 — Navire qui en rattrape un autre", "polarity": "affirmative",
     "fr": {"stem": "Un navire en rattrape un autre. Qui doit s'écarter ?",
            "explanation": "RIPAM règle 13 : le navire RATTRAPANT doit s'écarter du "
            "navire rattrapé, quelle que soit la nature des deux navires (même un "
            "voilier rattrapant un navire à moteur)."},
     "en": {"stem": "One vessel is overtaking another. Which must keep out of the way?",
            "explanation": "COLREG rule 13: the OVERTAKING vessel keeps clear of the "
            "one being overtaken, whatever the type of either vessel."},
     "choices": [
         {"fr": "Le navire qui rattrape", "en": "The overtaking vessel", "correct": True},
         {"fr": "Le navire rattrapé", "en": "The vessel being overtaken", "correct": False},
         {"fr": "Toujours le voilier", "en": "Always the sailing vessel", "correct": False}]},

    {"option": "cotiere", "theme": "regles_route", "source": "ripam",
     "ref": "RIPAM règle 18 — Responsabilités réciproques", "polarity": "affirmative",
     "fr": {"stem": "En l'absence de rattrapage et hors chenal étroit, un navire à "
            "moteur rencontre un voilier en train de naviguer à la voile. Qui s'écarte ?",
            "explanation": "RIPAM règle 18 : le navire à moteur doit s'écarter de la "
            "route du voilier (sous voiles)."},
     "en": {"stem": "Not overtaking and outside a narrow channel, a power-driven "
            "vessel meets a vessel under sail. Which one keeps clear?",
            "explanation": "COLREG rule 18: the power-driven vessel keeps out of the "
            "way of the sailing vessel."},
     "choices": [
         {"fr": "Le navire à moteur", "en": "The power-driven vessel", "correct": True},
         {"fr": "Le voilier", "en": "The sailing vessel", "correct": False},
         {"fr": "Aucun, ils gardent leur cap", "en": "Neither, both hold their course",
          "correct": False}]},

    {"option": "cotiere", "theme": "regles_route", "source": "ripam",
     "ref": "RIPAM règle 17 — Navire privilégié", "polarity": "affirmative",
     "fr": {"stem": "Vous êtes le navire « privilégié » qui doit maintenir cap et "
            "vitesse, mais l'autre ne manœuvre pas et l'abordage devient imminent. "
            "Que pouvez-vous faire ?",
            "explanation": "RIPAM règle 17 : si l'autre n'agit pas, le privilégié "
            "peut puis doit manœuvrer pour éviter seul l'abordage."},
     "en": {"stem": "You are the stand-on vessel that must keep course and speed, but "
            "the other vessel takes no action and collision becomes imminent. What "
            "may you do?",
            "explanation": "COLREG rule 17: if the give-way vessel fails to act, the "
            "stand-on vessel may, then must, manoeuvre to avoid collision on its own."},
     "choices": [
         {"fr": "Manœuvrer pour éviter seul l'abordage", "en": "Manoeuvre to avoid "
          "the collision yourself", "correct": True},
         {"fr": "Garder le cap et la vitesse quoi qu'il arrive", "en": "Hold course "
          "and speed no matter what", "correct": False},
         {"fr": "Accélérer pour passer devant", "en": "Speed up to cross ahead",
          "correct": False}]},

    # --- Feux, marques et signaux ------------------------------------------
    {"option": "cotiere", "theme": "feux_signaux", "source": "ripam",
     "ref": "RIPAM règle 23 — Feux d'un navire à moteur", "polarity": "affirmative",
     "fr": {"stem": "De nuit, un navire à moteur de moins de 50 m faisant route "
            "porte des feux de côté. De quelle couleur est le feu de BÂBORD ?",
            "explanation": "RIPAM : feu de côté bâbord ROUGE, tribord vert ; plus un "
            "feu de tête de mât blanc et un feu de poupe blanc."},
     "en": {"stem": "At night, an underway power-driven vessel under 50 m shows "
            "sidelights. What colour is the PORT sidelight?",
            "explanation": "COLREG: port sidelight RED, starboard green; plus a white "
            "masthead light and a white sternlight."},
     "choices": [
         {"fr": "Rouge", "en": "Red", "correct": True},
         {"fr": "Vert", "en": "Green", "correct": False},
         {"fr": "Blanc", "en": "White", "correct": False}]},

    {"option": "cotiere", "theme": "feux_signaux", "source": "ripam",
     "ref": "RIPAM règle 34 — Signaux de manœuvre (1 son bref)",
     "polarity": "affirmative",
     "fr": {"stem": "En vue d'un autre navire, un navire à moteur émet UN son bref. "
            "Qu'annonce-t-il ?",
            "explanation": "RIPAM règle 34 : un son bref = « Je viens sur tribord »."},
     "en": {"stem": "In sight of another vessel, a power-driven vessel sounds ONE "
            "short blast. What is it signalling?",
            "explanation": "COLREG rule 34: one short blast = “I am altering my "
            "course to starboard”."},
     "choices": [
         {"fr": "« Je viens sur tribord »", "en": "“I am altering to starboard”",
          "correct": True},
         {"fr": "« Je viens sur bâbord »", "en": "“I am altering to port”",
          "correct": False},
         {"fr": "« Je bats en arrière »", "en": "“I am operating astern”",
          "correct": False}]},

    {"option": "cotiere", "theme": "feux_signaux", "source": "ripam",
     "ref": "RIPAM règle 34 — Signaux de manœuvre (3 sons brefs)",
     "polarity": "affirmative",
     "fr": {"stem": "Que signifient TROIS sons brefs émis par un navire à moteur en "
            "vue d'un autre ?",
            "explanation": "RIPAM règle 34 : trois sons brefs = « Mes machines "
            "battent en arrière »."},
     "en": {"stem": "What do THREE short blasts from a power-driven vessel in sight "
            "of another mean?",
            "explanation": "COLREG rule 34: three short blasts = “I am operating "
            "astern propulsion”."},
     "choices": [
         {"fr": "« Mes machines battent en arrière »", "en": "“I am operating "
          "astern propulsion”", "correct": True},
         {"fr": "« Je viens sur bâbord »", "en": "“I am altering to port”",
          "correct": False},
         {"fr": "« Je suis échoué »", "en": "“I am aground”", "correct": False}]},

    {"option": "cotiere", "theme": "feux_signaux", "source": "ripam",
     "ref": "RIPAM règle 34 — Signal de doute", "polarity": "affirmative",
     "fr": {"stem": "Que signifient au moins CINQ sons brefs et rapprochés ?",
            "explanation": "RIPAM règle 34 d) : au moins cinq sons brefs et rapprochés "
            "expriment le doute sur les intentions ou la manœuvre de l'autre navire "
            "(signal d'avertissement)."},
     "en": {"stem": "What do at least FIVE short and rapid blasts mean?",
            "explanation": "COLREG rule 34(d): at least five short rapid blasts signal "
            "doubt about the other vessel's intentions or manoeuvre (a warning)."},
     "choices": [
         {"fr": "Un doute / un avertissement sur la manœuvre de l'autre", "en": "Doubt "
          "/ a warning about the other's manoeuvre", "correct": True},
         {"fr": "Une invitation à passer devant", "en": "An invitation to cross ahead",
          "correct": False},
         {"fr": "Un appel de détresse", "en": "A distress call", "correct": False}]},

    {"option": "cotiere", "theme": "feux_signaux", "source": "ripam",
     "ref": "RIPAM règle 35 — Signaux par visibilité réduite", "polarity": "affirmative",
     "fr": {"stem": "Par visibilité réduite (brouillard), quel signal émet un navire "
            "à moteur faisant route et ayant de l'erre ?",
            "explanation": "RIPAM règle 35 : un son prolongé à intervalles ne "
            "dépassant pas 2 minutes."},
     "en": {"stem": "In restricted visibility (fog), what signal does a power-driven "
            "vessel underway and making way sound?",
            "explanation": "COLREG rule 35: one prolonged blast at intervals of no "
            "more than 2 minutes."},
     "choices": [
         {"fr": "Un son prolongé toutes les 2 minutes au plus", "en": "One prolonged "
          "blast at least every 2 minutes", "correct": True},
         {"fr": "Trois sons brefs toutes les minutes", "en": "Three short blasts every "
          "minute", "correct": False},
         {"fr": "Aucun signal n'est nécessaire", "en": "No signal is required",
          "correct": False}]},

    {"option": "cotiere", "theme": "feux_signaux", "source": "ripam",
     "ref": "RIPAM annexe IV §1(i) — signaux de détresse (fusée à parachute rouge)", "polarity": "affirmative",
     "fr": {"stem": "Parmi ces moyens, lequel est un signal de détresse PYROTECHNIQUE "
            "reconnu en mer ?",
            "explanation": "La fusée à parachute à lumière rouge est un signal de "
            "détresse reconnu ; le fumigène orange l'est aussi de jour."},
     "en": {"stem": "Which of these is a recognised PYROTECHNIC distress signal at sea?",
            "explanation": "A red parachute rocket flare is a recognised distress "
            "signal; orange smoke also serves by day."},
     "choices": [
         {"fr": "Une fusée à parachute rouge", "en": "A red parachute flare",
          "correct": True},
         {"fr": "Un feu vert clignotant", "en": "A flashing green light", "correct": False},
         {"fr": "Un pavillon jaune hissé", "en": "A hoisted yellow flag", "correct": False}]},

    # --- Sécurité et matériel d'armement (Division 240) --------------------
    {"option": "cotiere", "theme": "securite", "source": "decret_2007",
     "ref": "Décret n° 2007-1167 du 2 août 2007, art. 2 — portée de l'option côtière (6 milles)", "polarity": "affirmative",
     "fr": {"stem": "Jusqu'à quelle distance d'un abri le permis plaisance option "
            "côtière autorise-t-il la navigation ?",
            "explanation": "L'option côtière autorise la navigation jusqu'à 6 milles "
            "nautiques d'un abri, de jour comme de nuit, quelle que soit la puissance."},
     "en": {"stem": "Up to what distance from a shelter does the côtière option of the "
            "permis plaisance authorise navigation?",
            "explanation": "The côtière option allows navigation up to 6 nautical miles "
            "from a shelter, day and night, regardless of engine power."},
     "choices": [
         {"fr": "6 milles nautiques", "en": "6 nautical miles", "correct": True},
         {"fr": "2 milles nautiques", "en": "2 nautical miles", "correct": False},
         {"fr": "Sans aucune limite de distance", "en": "With no distance limit",
          "correct": False}]},

    {"option": "cotiere", "theme": "securite", "source": "division_240",
     "ref": "Division 240, art. 240-2.04 §3 — EIF niveau 100 (zone côtière 2–6 MN)",
     "polarity": "affirmative",
     "fr": {"stem": "Pour la navigation côtière (jusqu'à 6 milles d'un abri), quelle "
            "flottabilité minimale doit avoir l'équipement individuel de flottabilité "
            "(brassière) selon la Division 240 ?",
            "explanation": "Division 240 : au moins 100 newtons pour la zone côtière "
            "(au-delà de 2 et jusqu'à 6 milles) ; 50 N en basique, 150 N au hauturier."},
     "en": {"stem": "For coastal navigation (up to 6 miles from a shelter), what "
            "minimum buoyancy must the personal flotation device have under Division 240?",
            "explanation": "Division 240: at least 100 newtons for the coastal zone "
            "(beyond 2 and up to 6 miles); 50 N inshore, 150 N offshore."},
     "choices": [
         {"fr": "100 N", "en": "100 N", "correct": True},
         {"fr": "50 N", "en": "50 N", "correct": False},
         {"fr": "10 N", "en": "10 N", "correct": False}]},

    {"option": "cotiere", "theme": "securite", "source": "directive_2013_53",
     "ref": "Directive 2013/53/UE, annexe I, partie A — catégories de conception (C : force 6, vagues 2 m)", "polarity": "affirmative",
     "fr": {"stem": "À quel programme de navigation correspond la catégorie de "
            "conception « C » d'un bateau de plaisance ?",
            "explanation": "Catégorie C = « à proximité de la côte » : conçue pour un "
            "vent jusqu'à force 6 et des vagues jusqu'à 2 m. (A = haute mer, B = au "
            "large, D = eaux abritées.)"},
     "en": {"stem": "Which navigation programme does design category “C” of a "
            "pleasure boat correspond to?",
            "explanation": "Category C = “inshore”: designed for winds up to "
            "force 6 and waves up to 2 m. (A = ocean, B = offshore, D = sheltered waters.)"},
     "choices": [
         {"fr": "À proximité de la côte (force 6, vagues 2 m)", "en": "Inshore (force "
          "6, 2 m waves)", "correct": True},
         {"fr": "En haute mer sans restriction", "en": "Unrestricted ocean", "correct": False},
         {"fr": "En eaux abritées uniquement", "en": "Sheltered waters only",
          "correct": False}]},

    {"option": "cotiere", "theme": "securite", "source": "division_240",
     "ref": "Division 240, art. 240-2.01 §1 — nombre maximal de personnes (plaque constructeur)", "polarity": "affirmative",
     "fr": {"stem": "Combien de personnes peut-on légalement embarquer à bord d'un "
            "bateau de plaisance ?",
            "explanation": "Au maximum le nombre fixé par le constructeur, indiqué sur "
            "la plaque signalétique / la catégorie de conception du bateau."},
     "en": {"stem": "How many people may legally be carried aboard a pleasure boat?",
            "explanation": "At most the number set by the builder, shown on the boat's "
            "builder's plate / design category."},
     "choices": [
         {"fr": "Le nombre maximal fixé par le constructeur", "en": "The maximum set "
          "by the builder", "correct": True},
         {"fr": "Autant qu'il y a de gilets à bord", "en": "As many as there are "
          "lifejackets aboard", "correct": False},
         {"fr": "Aucune limite en mer", "en": "No limit at sea", "correct": False}]},

    # --- Météorologie et marées --------------------------------------------
    {"option": "cotiere", "theme": "meteo_maree", "source": "shom",
     "ref": "SHOM — zéro hydrographique (sondes des cartes marines)", "polarity": "affirmative",
     "fr": {"stem": "Sur une carte marine, par rapport à quel niveau les profondeurs "
            "(sondes) sont-elles indiquées ?",
            "explanation": "Les sondes sont rapportées au zéro hydrographique, proche "
            "du niveau des plus basses mers : la profondeur réelle est généralement "
            "supérieure."},
     "en": {"stem": "On a nautical chart, relative to what level are the depths "
            "(soundings) given?",
            "explanation": "Soundings are referred to chart datum, close to the level "
            "of the lowest tides: actual depth is usually greater."},
     "choices": [
         {"fr": "Le zéro hydrographique (plus basses mers)", "en": "Chart datum "
          "(lowest tides)", "correct": True},
         {"fr": "Le niveau moyen de la mer", "en": "Mean sea level", "correct": False},
         {"fr": "Le niveau de pleine mer", "en": "High-water level", "correct": False}]},

    {"option": "cotiere", "theme": "meteo_maree", "source": "shom",
     "ref": "SHOM — marnage (pleine mer / basse mer consécutives)", "polarity": "affirmative",
     "fr": {"stem": "Qu'appelle-t-on le « marnage » ?",
            "explanation": "Le marnage est la différence de hauteur d'eau entre une "
            "pleine mer et la basse mer qui la suit (ou la précède)."},
     "en": {"stem": "What is the “tidal range” (marnage)?",
            "explanation": "The tidal range is the height difference between a high "
            "water and the following (or preceding) low water."},
     "choices": [
         {"fr": "La différence de hauteur entre pleine mer et basse mer", "en": "The "
          "height difference between high and low water", "correct": True},
         {"fr": "La vitesse du courant de marée", "en": "The speed of the tidal stream",
          "correct": False},
         {"fr": "La durée d'une marée", "en": "The duration of a tide", "correct": False}]},

    {"option": "cotiere", "theme": "meteo_maree", "source": "shom",
     "ref": "SHOM — coefficient de marée (échelle 20 à 120)", "polarity": "affirmative",
     "fr": {"stem": "Entre quelles valeurs le coefficient de marée varie-t-il ?",
            "explanation": "Le coefficient de marée varie de 20 (très faible morte-eau) "
            "à 120 (très forte vive-eau) ; 95 marque le seuil des grandes marées."},
     "en": {"stem": "Between what values does the tidal coefficient vary?",
            "explanation": "The tidal coefficient ranges from 20 (very weak neap) to "
            "120 (very strong spring); 95 marks the threshold of large tides."},
     "choices": [
         {"fr": "Entre 20 et 120", "en": "Between 20 and 120", "correct": True},
         {"fr": "Entre 0 et 100", "en": "Between 0 and 100", "correct": False},
         {"fr": "Entre 1 et 12", "en": "Between 1 and 12", "correct": False}]},

    {"option": "cotiere", "theme": "meteo_maree", "source": "meteo_france",
     "ref": "Échelle de Beaufort 0–12 (OMM / Météo-France)", "polarity": "affirmative",
     "fr": {"stem": "L'échelle de Beaufort, qui mesure la force du vent, est graduée "
            "de 0 à combien ?",
            "explanation": "L'échelle de Beaufort va de la force 0 (calme) à la force "
            "12 (ouragan)."},
     "en": {"stem": "The Beaufort scale, measuring wind force, is graduated from 0 to "
            "what value?",
            "explanation": "The Beaufort scale runs from force 0 (calm) to force 12 "
            "(hurricane)."},
     "choices": [
         {"fr": "12", "en": "12", "correct": True},
         {"fr": "10", "en": "10", "correct": False},
         {"fr": "100", "en": "100", "correct": False}]},

    {"option": "cotiere", "theme": "meteo_maree", "source": "shom",
     "ref": "Marées — règle des douzièmes (méthode standard, SHOM)", "polarity": "affirmative",
     "fr": {"stem": "À quoi sert la « règle des douzièmes » ?",
            "explanation": "Elle permet d'estimer la hauteur d'eau à un instant donné "
            "entre la basse mer et la pleine mer (1/12, 2/12, 3/12, 3/12, 2/12, 1/12 "
            "par heure)."},
     "en": {"stem": "What is the “rule of twelfths” used for?",
            "explanation": "It estimates the height of water at a given time between "
            "low and high water (1/12, 2/12, 3/12, 3/12, 2/12, 1/12 per hour)."},
     "choices": [
         {"fr": "Estimer la hauteur d'eau à une heure donnée de la marée", "en": "To "
          "estimate the water height at a given hour of the tide", "correct": True},
         {"fr": "Calculer la force du vent", "en": "To calculate the wind force",
          "correct": False},
         {"fr": "Mesurer la dérive due au courant", "en": "To measure drift from the "
          "current", "correct": False}]},

    # --- Réglementation, permis et radio -----------------------------------
    {"option": "cotiere", "theme": "reglementation", "source": "itu_rr",
     "ref": "UIT, Règlement des radiocommunications, appendice 18 — VHF canal 16 (156,8 MHz)", "polarity": "affirmative",
     "fr": {"stem": "Quel canal VHF est réservé à la veille de détresse, d'urgence "
            "et de sécurité, ainsi qu'à l'appel ?",
            "explanation": "Le canal 16 est le canal international de détresse, "
            "d'urgence, de sécurité et d'appel."},
     "en": {"stem": "Which VHF channel is reserved for distress, urgency and safety "
            "watch, and for calling?",
            "explanation": "Channel 16 is the international distress, urgency, safety "
            "and calling channel."},
     "choices": [
         {"fr": "Le canal 16", "en": "Channel 16", "correct": True},
         {"fr": "Le canal 6", "en": "Channel 6", "correct": False},
         {"fr": "Le canal 72", "en": "Channel 72", "correct": False}]},

    {"option": "cotiere", "theme": "reglementation", "source": "itu_rr",
     "ref": "UIT, Règlement des radiocommunications, art. 32 — détresse (MAYDAY)", "polarity": "affirmative",
     "fr": {"stem": "Un message radio commençant par « MAYDAY » correspond à quel "
            "degré de priorité ?",
            "explanation": "« MAYDAY » = détresse : danger grave et imminent, "
            "assistance immédiate. « PAN PAN » = urgence ; « SÉCURITÉ » = sécurité."},
     "en": {"stem": "A radio message beginning with “MAYDAY” corresponds to "
            "which priority level?",
            "explanation": "“MAYDAY” = distress: grave and imminent danger, "
            "immediate help. “PAN PAN” = urgency; “SÉCURITÉ” = safety."},
     "choices": [
         {"fr": "La détresse", "en": "Distress", "correct": True},
         {"fr": "L'urgence", "en": "Urgency", "correct": False},
         {"fr": "La sécurité", "en": "Safety", "correct": False}]},

    {"option": "cotiere", "theme": "reglementation", "source": "decret_2007",
     "ref": "Décret n° 2007-1167 du 2 août 2007, art. 2 — permis exigé au-delà de 4,5 kW", "polarity": "affirmative",
     "fr": {"stem": "À partir de quelle puissance du moteur le permis plaisance "
            "est-il obligatoire ?",
            "explanation": "Le permis est exigé pour conduire un bateau de plaisance "
            "à moteur d'une puissance supérieure à 4,5 kW (environ 6 ch)."},
     "en": {"stem": "Above what engine power is the permis plaisance required?",
            "explanation": "The licence is required to drive a motor pleasure boat "
            "whose power exceeds 4.5 kW (about 6 hp)."},
     "choices": [
         {"fr": "Plus de 4,5 kW (≈ 6 ch)", "en": "More than 4.5 kW (≈ 6 hp)",
          "correct": True},
         {"fr": "Plus de 1 kW", "en": "More than 1 kW", "correct": False},
         {"fr": "Plus de 50 ch", "en": "More than 50 hp", "correct": False}]},

    {"option": "cotiere", "theme": "reglementation", "source": "decret_2007",
     "ref": "Décret n° 2007-1167 du 2 août 2007, art. 3 — âge minimal (16 ans)", "polarity": "affirmative",
     "fr": {"stem": "À partir de quel âge peut-on obtenir le permis plaisance "
            "(option côtière) ?",
            "explanation": "L'âge minimal pour obtenir le permis plaisance est de "
            "16 ans."},
     "en": {"stem": "From what age can the permis plaisance (côtière option) be "
            "obtained?",
            "explanation": "The minimum age to obtain the permis plaisance is 16."},
     "choices": [
         {"fr": "16 ans", "en": "16 years", "correct": True},
         {"fr": "14 ans", "en": "14 years", "correct": False},
         {"fr": "18 ans", "en": "18 years", "correct": False}]},

    # --- Protection de l'environnement -------------------------------------
    {"option": "cotiere", "theme": "environnement", "source": "code_environnement",
     "ref": "Code de l'environnement, art. L.218-11 et s. / MARPOL annexes I et V", "polarity": "affirmative",
     "fr": {"stem": "En mer, que dit la réglementation sur le rejet des détritus et "
            "des hydrocarbures ?",
            "explanation": "Le rejet à la mer des détritus, ordures et hydrocarbures "
            "est interdit ; les déchets doivent être rapportés à terre."},
     "en": {"stem": "At sea, what does the regulation say about discharging rubbish "
            "and hydrocarbons?",
            "explanation": "Discharging rubbish and hydrocarbons into the sea is "
            "prohibited; waste must be brought back ashore."},
     "choices": [
         {"fr": "Il est interdit", "en": "It is prohibited", "correct": True},
         {"fr": "Il est libre au-delà de 3 milles", "en": "It is free beyond 3 miles",
          "correct": False},
         {"fr": "Il est autorisé la nuit", "en": "It is allowed at night",
          "correct": False}]},

    {"option": "cotiere", "theme": "environnement", "source": "code_environnement",
     "ref": "MARPOL annexe V / Code de l'environnement — déchets rapportés à terre", "polarity": "affirmative",
     "fr": {"stem": "Que doit faire le plaisancier de ses déchets produits à bord ?",
            "explanation": "Il doit les conserver à bord puis les déposer à terre dans "
            "les installations de collecte du port."},
     "en": {"stem": "What should the boater do with waste produced aboard?",
            "explanation": "Keep it aboard and dispose of it ashore in the harbour's "
            "collection facilities."},
     "choices": [
         {"fr": "Les rapporter à terre dans les installations portuaires", "en": "Bring "
          "it ashore to harbour facilities", "correct": True},
         {"fr": "Les jeter au large", "en": "Throw it overboard offshore", "correct": False},
         {"fr": "Les brûler à bord", "en": "Burn it aboard", "correct": False}]},

    # --- Compléments option côtière (banque portée à 40) -------------------
    # Balisage (IALA région A)
    {"option": "cotiere", "theme": "balisage", "source": "iala_a",
     "ref": "Balisage IALA — marque cardinale Sud", "polarity": "affirmative",
     "fr": {"stem": "Comment reconnaît-on le voyant d'une marque cardinale SUD, et de "
            "quel côté faut-il passer ?",
            "explanation": "Cardinale Sud : deux cônes noirs superposés, pointes vers le "
            "BAS ; les eaux saines sont au sud, on passe donc au sud de la marque."},
     "en": {"stem": "How is a SOUTH cardinal mark's topmark recognised, and which side "
            "do you pass?",
            "explanation": "South cardinal: two black cones pointing DOWN; safe water is "
            "to the south, so pass to the south of the mark."},
     "choices": [
         {"fr": "Deux cônes pointes vers le bas ; on passe au sud", "en": "Two cones "
          "pointing down; pass to the south", "correct": True},
         {"fr": "Deux cônes pointes vers le haut ; on passe au nord", "en": "Two cones "
          "pointing up; pass to the north", "correct": False},
         {"fr": "Deux cônes base contre base ; on passe à l'est", "en": "Two cones base "
          "to base; pass to the east", "correct": False}]},

    {"option": "cotiere", "theme": "balisage", "source": "iala_a",
     "ref": "Balisage IALA — marque spéciale", "polarity": "affirmative",
     "fr": {"stem": "Que signale une marque entièrement JAUNE, éventuellement surmontée "
            "d'une croix de Saint-André (X) jaune ?",
            "explanation": "C'est une marque spéciale : elle délimite une zone ou un "
            "dispositif particulier (baignade, chenal, conduite immergée, zone "
            "réglementée) et ne marque pas en soi un danger de navigation."},
     "en": {"stem": "What does an all-YELLOW mark, possibly with a yellow St Andrew's "
            "cross (X) topmark, indicate?",
            "explanation": "A special mark: it bounds a special area or feature (bathing "
            "zone, channel, pipeline, restricted area) and does not itself mark a "
            "navigational danger."},
     "choices": [
         {"fr": "Une zone ou un dispositif particulier (marque spéciale)", "en": "A "
          "special area or feature (special mark)", "correct": True},
         {"fr": "Un danger isolé à éviter", "en": "An isolated danger to avoid",
          "correct": False},
         {"fr": "Le côté tribord du chenal", "en": "The starboard side of the channel",
          "correct": False}]},

    # Règles de barre et de route (RIPAM)
    {"option": "cotiere", "theme": "regles_route", "source": "ripam",
     "ref": "RIPAM règle 9 — Chenaux étroits", "polarity": "affirmative",
     "fr": {"stem": "Dans un chenal étroit, de quel côté un navire doit-il en règle "
            "générale se tenir ?",
            "explanation": "RIPAM règle 9 : il serre, dans la mesure du possible et "
            "sans danger, le bord extérieur du chenal situé sur SA droite (tribord)."},
     "en": {"stem": "In a narrow channel, to which side must a vessel generally keep?",
            "explanation": "COLREG rule 9: keep as near as is safe to the outer limit of "
            "the channel that lies on its STARBOARD side."},
     "choices": [
         {"fr": "Le bord du chenal situé sur sa droite (tribord)", "en": "The channel "
          "edge on its starboard side", "correct": True},
         {"fr": "Le milieu du chenal", "en": "The middle of the channel", "correct": False},
         {"fr": "Le bord situé sur sa gauche (bâbord)", "en": "The edge on its port side",
          "correct": False}]},

    # Feux, marques et signaux (RIPAM)
    {"option": "cotiere", "theme": "feux_signaux", "source": "ripam",
     "ref": "RIPAM règle 30 — Navire au mouillage", "polarity": "affirmative",
     "fr": {"stem": "De nuit, un navire de moins de 50 m au mouillage montre :",
            "explanation": "RIPAM règle 30 : un feu blanc visible sur tout l'horizon, "
            "placé à l'avant ; de jour, une boule noire à l'avant."},
     "en": {"stem": "At night, a vessel under 50 m at anchor shows:",
            "explanation": "COLREG rule 30: an all-round white light forward; by day, a "
            "black ball forward."},
     "choices": [
         {"fr": "Un feu blanc visible sur tout l'horizon", "en": "An all-round white "
          "light", "correct": True},
         {"fr": "Un feu rouge visible sur tout l'horizon", "en": "An all-round red light",
          "correct": False},
         {"fr": "Deux feux verts superposés", "en": "Two green lights in a vertical line",
          "correct": False}]},

    # Sécurité et matériel d'armement (Division 240)
    {"option": "cotiere", "theme": "securite", "source": "division_240",
     "ref": "Division 240, art. 240-2.01 §7 — coupe-circuit (barre franche / déporté / VNM)", "polarity": "affirmative",
     "fr": {"stem": "Sur un bateau à moteur conduit à la barre franche, pourquoi le "
            "conducteur doit-il porter le coupe-circuit (cordon) relié à lui ?",
            "explanation": "En cas de chute à l'eau, le cordon se détache et coupe "
            "aussitôt le moteur : le bateau ne part pas seul et ne blesse pas l'homme "
            "à la mer."},
     "en": {"stem": "On a tiller-steered motorboat, why must the driver wear the engine "
            "kill-cord attached to themselves?",
            "explanation": "If they fall overboard, the cord pulls free and instantly "
            "stops the engine: the boat cannot run off or injure the person in the water."},
     "choices": [
         {"fr": "Il coupe le moteur si le conducteur tombe à l'eau", "en": "It stops the "
          "engine if the driver falls overboard", "correct": True},
         {"fr": "Il augmente la vitesse du moteur", "en": "It increases engine speed",
          "correct": False},
         {"fr": "Il sert d'antivol au port", "en": "It serves as an anti-theft device in "
          "port", "correct": False}]},

    # Météorologie et marées
    {"option": "cotiere", "theme": "meteo_maree", "source": "shom",
     "ref": "SHOM — étale (de niveau)", "polarity": "affirmative",
     "fr": {"stem": "Qu'appelle-t-on l'« étale » de marée ?",
            "explanation": "C'est le court moment, à la pleine ou à la basse mer, où le "
            "niveau de l'eau ne varie plus (étale de niveau). La renverse du courant — l'étale de courant — est un phénomène voisin mais distinct, qui ne coïncide pas nécessairement."},
     "en": {"stem": "What is the tidal “slack” (étale)?",
            "explanation": "The brief moment, at high or low water, when the level stops "
            "changing (slack of the level). The current's turn (slack of stream) is a related but distinct event that need not coincide."},
     "choices": [
         {"fr": "Le moment où le niveau ne varie plus (étale de niveau)", "en": "When the "
          "water level stops changing (slack of the level)", "correct": True},
         {"fr": "Le moment où le courant est le plus fort", "en": "When the current is "
          "strongest", "correct": False},
         {"fr": "La différence entre pleine et basse mer", "en": "The difference between "
          "high and low water", "correct": False}]},

    # Réglementation, permis et radio
    {"option": "cotiere", "theme": "reglementation", "source": "prefet_maritime",
     "ref": "Arrêté du préfet maritime (bande des 300 m, 5 nœuds) ; CGCT art. L.2213-23", "polarity": "affirmative",
     "fr": {"stem": "Dans la bande littorale des 300 mètres à partir du rivage, à "
            "quelle vitesse la navigation est-elle en principe limitée ?",
            "explanation": "Sauf disposition locale particulière, la vitesse est limitée "
            "à 5 nœuds dans la bande des 300 mètres, pour la sécurité des baigneurs."},
     "en": {"stem": "Within the 300-metre coastal band from the shore, what is the "
            "navigation speed generally limited to?",
            "explanation": "Unless a local rule says otherwise, speed is limited to "
            "5 knots within the 300-metre band, for the safety of swimmers."},
     "choices": [
         {"fr": "5 nœuds", "en": "5 knots", "correct": True},
         {"fr": "20 nœuds", "en": "20 knots", "correct": False},
         {"fr": "Aucune limite de vitesse", "en": "No speed limit", "correct": False}]},

    {"option": "cotiere", "theme": "reglementation", "source": "itu_rr",
     "ref": "UIT, Règlement des radiocommunications, art. 33 — urgence (PAN PAN)", "polarity": "affirmative",
     "fr": {"stem": "Un message radio commençant par « PAN PAN » correspond à quel "
            "degré de priorité ?",
            "explanation": "« PAN PAN » = urgence : la sécurité d'un navire ou d'une "
            "personne est compromise, sans le danger grave et imminent qui justifierait "
            "la détresse (MAYDAY)."},
     "en": {"stem": "A radio message beginning with “PAN PAN” corresponds to which "
            "priority level?",
            "explanation": "“PAN PAN” = urgency: the safety of a vessel or person is at "
            "risk, without the grave and imminent danger that warrants distress (MAYDAY)."},
     "choices": [
         {"fr": "L'urgence", "en": "Urgency", "correct": True},
         {"fr": "La détresse", "en": "Distress", "correct": False},
         {"fr": "La sécurité (bulletin météo)", "en": "Safety (weather bulletin)",
          "correct": False}]},

    # Protection de l'environnement
    {"option": "cotiere", "theme": "environnement", "source": "prefet_maritime",
     "ref": "PREMAR Méditerranée, arrêté n° 123/2019, art. 6 — mouillage / posidonie", "polarity": "affirmative",
     "fr": {"stem": "En Méditerranée, sur les herbiers de posidonie, le mouillage de "
            "l'ancre est :",
            "explanation": "Réglementé, voire interdit dans de nombreuses zones : l'ancre "
            "arrache ces herbiers protégés, essentiels à la vie marine ; on utilise les "
            "zones ou bouées de mouillage prévues."},
     "en": {"stem": "In the Mediterranean, anchoring on Posidonia seagrass beds is:",
            "explanation": "Regulated, and prohibited in many areas: the anchor tears up "
            "these protected beds, vital to marine life; use the designated anchoring "
            "zones or buoys."},
     "choices": [
         {"fr": "Réglementé, voire interdit (herbiers protégés)", "en": "Regulated, even "
          "prohibited (protected beds)", "correct": True},
         {"fr": "Libre et sans conséquence", "en": "Free and harmless", "correct": False},
         {"fr": "Recommandé car l'ancre y tient bien", "en": "Recommended because the "
          "anchor holds well there", "correct": False}]},

    # ======================= OPTION EAUX INTÉRIEURES =======================

    # --- Voies navigables et stationnement ---------------------------------
    {"option": "eaux_interieures", "theme": "voies_navigables", "source": "rgp",
     "ref": "RGP (Code des transports, art. R.4000-2, 7°) — menue embarcation (< 20 m)", "polarity": "affirmative",
     "fr": {"stem": "Au sens du règlement général de police (RGP), qu'est-ce qu'une "
            "« menue embarcation » ?",
            "explanation": "C'est, en règle générale, un bateau dont la longueur de "
            "coque est inférieure à 20 mètres (hors bateaux à passagers, remorqueurs, "
            "etc.)."},
     "en": {"stem": "Under the inland navigation police regulation (RGP), what is a "
            "“small craft” (menue embarcation)?",
            "explanation": "As a rule, a vessel with a hull length under 20 metres "
            "(excluding passenger vessels, tugs, etc.)."},
     "choices": [
         {"fr": "Un bateau de moins de 20 mètres", "en": "A vessel under 20 metres",
          "correct": True},
         {"fr": "Tout bateau de moins de 24 mètres", "en": "Any vessel under 24 metres",
          "correct": False},
         {"fr": "Un bateau de moins de 15 mètres uniquement", "en": "A vessel under 15 "
          "metres only", "correct": False}]},

    {"option": "eaux_interieures", "theme": "voies_navigables", "source": "rgp",
     "ref": "RGP, art. A.4241-54-2 — stationnement interdit (ponts, passages étroits)", "polarity": "affirmative",
     "fr": {"stem": "Où le stationnement (l'arrêt) d'un bateau est-il en principe "
            "interdit sur une voie navigable ?",
            "explanation": "Le stationnement est interdit là où il gêne la navigation "
            "(sous les ponts, dans les passages étroits) et partout où la "
            "signalisation l'interdit."},
     "en": {"stem": "Where is mooring (stopping) of a vessel generally prohibited on a "
            "waterway?",
            "explanation": "Mooring is forbidden where it hampers navigation (under "
            "bridges, in narrow passages) and wherever a sign prohibits it."},
     "choices": [
         {"fr": "Sous les ponts et dans les passages étroits", "en": "Under bridges "
          "and in narrow passages", "correct": True},
         {"fr": "Le long de tous les quais aménagés", "en": "Along every fitted quay",
          "correct": False},
         {"fr": "Nulle part, le stationnement est libre", "en": "Nowhere — mooring is "
          "unrestricted", "correct": False}]},

    {"option": "eaux_interieures", "theme": "voies_navigables", "source": "rgp",
     "ref": "RGP, art. A.4241-53-21 — vitesse et batillage", "polarity": "affirmative",
     "fr": {"stem": "Pour limiter le batillage (les remous qui érodent les berges et "
            "secouent les bateaux amarrés), que doit faire le conducteur près des rives ?",
            "explanation": "Il doit réduire sa vitesse à l'approche des rives, des "
            "ports et des bateaux stationnés, afin de limiter les remous (batillage)."},
     "en": {"stem": "To limit wash (the wake that erodes banks and rocks moored boats), "
            "what must the driver do near the banks?",
            "explanation": "Reduce speed when approaching banks, harbours and moored "
            "boats, to limit the wash."},
     "choices": [
         {"fr": "Réduire sa vitesse", "en": "Reduce speed", "correct": True},
         {"fr": "Augmenter sa vitesse pour passer vite", "en": "Increase speed to pass "
          "quickly", "correct": False},
         {"fr": "Naviguer au plus près de la berge", "en": "Hug the bank as close as "
          "possible", "correct": False}]},

    # --- Écluses, barrages et ouvrages -------------------------------------
    {"option": "eaux_interieures", "theme": "ecluses", "source": "rgp",
     "ref": "RGP, art. A.4241-53-31 §1 — feux d'écluse (rouge = accès interdit)", "polarity": "affirmative",
     "fr": {"stem": "À l'entrée d'une écluse, que signifie un feu ROUGE ?",
            "explanation": "Un feu rouge isolé signifie « accès interdit » ; on attend. "
            "Le feu vert autorise l'entrée ; deux feux rouges = écluse hors service."},
     "en": {"stem": "At a lock entrance, what does a RED light mean?",
            "explanation": "A single red light means “no entry”; wait. A green "
            "light authorises entry; two red lights mean the lock is out of service."},
     "choices": [
         {"fr": "Entrée interdite, il faut attendre", "en": "Entry forbidden, you must "
          "wait", "correct": True},
         {"fr": "Entrée autorisée", "en": "Entry authorised", "correct": False},
         {"fr": "Sortie de l'écluse seulement", "en": "Exit from the lock only",
          "correct": False}]},

    {"option": "eaux_interieures", "theme": "ecluses", "source": "rgp",
     "ref": "RGP, art. A.4241-53-31 §1 — feu vert d'écluse (accès autorisé)", "polarity": "affirmative",
     "fr": {"stem": "Quel feu autorise l'entrée dans une écluse ?",
            "explanation": "Le feu vert autorise l'entrée. Deux feux rouges signifient "
            "que l'écluse est hors service."},
     "en": {"stem": "Which light authorises entry into a lock?",
            "explanation": "A green light authorises entry. Two red lights mean the "
            "lock is out of service."},
     "choices": [
         {"fr": "Le feu vert", "en": "The green light", "correct": True},
         {"fr": "Le feu rouge", "en": "The red light", "correct": False},
         {"fr": "Deux feux rouges", "en": "Two red lights", "correct": False}]},

    {"option": "eaux_interieures", "theme": "ecluses", "source": "rgp",
     "ref": "RGP, art. A.4241-53-30/-31 — conduite dans le sas d'écluse", "polarity": "affirmative",
     "fr": {"stem": "Dans le sas d'une écluse, comment doit-on tenir ses amarres "
            "pendant l'éclusée ?",
            "explanation": "Le niveau d'eau varie : il faut tenir les amarres et les "
            "filer ou les reprendre au fur et à mesure, sans jamais les frapper à "
            "poste fixe (risque de rupture ou de gîte)."},
     "en": {"stem": "In a lock chamber, how should you handle your lines during "
            "locking?",
            "explanation": "The water level changes: tend the lines and pay out or "
            "take in as needed, never make them fast to a fixed point (risk of parting "
            "or listing)."},
     "choices": [
         {"fr": "Les tenir et les ajuster, sans les frapper à poste fixe", "en": "Tend "
          "and adjust them, never made fast to a fixed point", "correct": True},
         {"fr": "Les frapper solidement à un taquet fixe", "en": "Make them fast hard "
          "to a fixed cleat", "correct": False},
         {"fr": "Retirer toutes les amarres", "en": "Remove all the lines",
          "correct": False}]},

    # --- Signalisation des voies et des bateaux ----------------------------
    {"option": "eaux_interieures", "theme": "signalisation_fluviale", "source": "rgp",
     "ref": "RGP, annexe 5, panneau A.1 — interdiction de passer", "polarity": "affirmative",
     "fr": {"stem": "Sur une voie navigable, que signifie un panneau rectangulaire à "
            "bord rouge barré d'une bande blanche horizontale ?",
            "explanation": "C'est un panneau d'interdiction (type A.1) : interdiction "
            "de passer / d'aller au-delà."},
     "en": {"stem": "On a waterway, what does a rectangular sign with a red border and "
            "a white horizontal bar mean?",
            "explanation": "It is a prohibition sign (type A.1): no entry / passage "
            "forbidden."},
     "choices": [
         {"fr": "Interdiction de passer", "en": "No passage / no entry", "correct": True},
         {"fr": "Obligation de s'arrêter pour faire le plein", "en": "Obligation to "
          "stop and refuel", "correct": False},
         {"fr": "Recommandation de ralentir", "en": "Recommendation to slow down",
          "correct": False}]},

    {"option": "eaux_interieures", "theme": "signalisation_fluviale", "source": "cevni",
     "ref": "CEVNI — signal général « Attention » (un son prolongé)", "polarity": "affirmative",
     "fr": {"stem": "Sur une voie intérieure, que signifie en règle générale UN son "
            "prolongé émis par un bateau ?",
            "explanation": "Un son prolongé est le signal « Attention » ; il attire "
            "l'attention des autres bateaux."},
     "en": {"stem": "On an inland waterway, what does ONE prolonged blast from a vessel "
            "generally mean?",
            "explanation": "One prolonged blast is the “Attention” signal; it "
            "draws other vessels' attention."},
     "choices": [
         {"fr": "« Attention »", "en": "“Attention”", "correct": True},
         {"fr": "« Je fais demi-tour »", "en": "“I am turning around”",
          "correct": False},
         {"fr": "« Je suis à l'arrêt »", "en": "“I am stopped”", "correct": False}]},

    {"option": "eaux_interieures", "theme": "signalisation_fluviale", "source": "rgp",
     "ref": "RGP, art. A.4241-48-13 — feux des menues embarcations motorisées (bâbord rouge)", "polarity": "affirmative",
     "fr": {"stem": "De nuit, un bateau motorisé faisant route en eaux intérieures "
            "porte un feu à bâbord. De quelle couleur est-il ?",
            "explanation": "Comme en mer : feu de côté bâbord rouge, tribord vert, plus "
            "un feu de mât blanc et un feu de poupe."},
     "en": {"stem": "At night, a power-driven vessel underway on inland waters shows a "
            "light to port. What colour is it?",
            "explanation": "As at sea: port sidelight red, starboard green, plus a "
            "white masthead light and a sternlight."},
     "choices": [
         {"fr": "Rouge", "en": "Red", "correct": True},
         {"fr": "Vert", "en": "Green", "correct": False},
         {"fr": "Jaune", "en": "Yellow", "correct": False}]},

    {"option": "eaux_interieures", "theme": "signalisation_fluviale", "source": "rgp",
     "ref": "RGP, art. A.4241-48-20 — signalisation en stationnement (feu blanc)", "polarity": "affirmative",
     "fr": {"stem": "De nuit, un bateau stationnant à l'écart de la rive, hors d'un "
            "port, porte le plus souvent :",
            "explanation": "Il porte un feu blanc ordinaire visible de tous les côtés, "
            "pour signaler sa présence aux autres bateaux."},
     "en": {"stem": "At night, a vessel moored away from the bank, outside a harbour, "
            "most often shows:",
            "explanation": "An ordinary white light visible all round, to signal its "
            "presence to other vessels."},
     "choices": [
         {"fr": "Un feu blanc visible de tous côtés", "en": "An all-round white light",
          "correct": True},
         {"fr": "Un feu rouge clignotant", "en": "A flashing red light", "correct": False},
         {"fr": "Aucun feu", "en": "No light", "correct": False}]},

    # --- Règles de route (fluvial) -----------------------------------------
    {"option": "eaux_interieures", "theme": "regles_route", "source": "rgp",
     "ref": "RGP, art. A.4241-53-3 — menues embarcations s'écartent des grands bateaux et bacs", "polarity": "affirmative",
     "fr": {"stem": "En eaux intérieures, vis-à-vis des grands bateaux, des bacs et "
            "des bateaux assurant un service régulier, les menues embarcations "
            "(plaisance) doivent :",
            "explanation": "Les menues embarcations doivent laisser la route libre aux "
            "grands bateaux, aux bacs et aux convois : elles s'en écartent."},
     "en": {"stem": "On inland waters, with respect to large vessels, ferries and "
            "vessels on a regular service, small craft (pleasure boats) must:",
            "explanation": "Small craft must leave the way clear for large vessels, "
            "ferries and convoys: they keep out of their way."},
     "choices": [
         {"fr": "S'écarter de leur route", "en": "Keep out of their way", "correct": True},
         {"fr": "Garder leur route, étant prioritaires", "en": "Hold their course, "
          "having priority", "correct": False},
         {"fr": "Les obliger à s'arrêter", "en": "Force them to stop", "correct": False}]},

    {"option": "eaux_interieures", "theme": "regles_route", "source": "rgp",
     "ref": "RGP, art. A.4241-53-6 §1 — venir sur tribord (croisement bâbord-bâbord)", "polarity": "affirmative",
     "fr": {"stem": "En règle générale sur une voie intérieure, de quel côté un "
            "bateau doit-il tenir sa route ?",
            "explanation": "Chaque bateau tient en principe sa droite (tribord) ; on "
            "se croise alors bâbord sur bâbord, sauf signalisation contraire."},
     "en": {"stem": "As a general rule on an inland waterway, to which side should a "
            "vessel keep?",
            "explanation": "Each vessel keeps to its right (starboard) as a rule; "
            "vessels then pass port to port, unless signs indicate otherwise."},
     "choices": [
         {"fr": "Sur sa droite (tribord)", "en": "To its right (starboard)",
          "correct": True},
         {"fr": "Sur sa gauche (bâbord)", "en": "To its left (port)", "correct": False},
         {"fr": "Au milieu du chenal", "en": "In the middle of the channel",
          "correct": False}]},

    {"option": "eaux_interieures", "theme": "regles_route", "source": "rgp",
     "ref": "RGP, art. A.4241-53-8 — passage étroit (priorité à l'avalant)", "polarity": "affirmative",
     "fr": {"stem": "Dans un passage étroit (sous un pont, un chenal resserré) où le "
            "croisement est impossible, que doit faire le conducteur ?",
            "explanation": "Il s'assure que le passage est libre avant de s'engager, "
            "et cède le passage selon la signalisation ; la priorité va au bateau "
            "avalant (descendant le courant) sur les rivières."},
     "en": {"stem": "In a narrow passage (under a bridge, a tight channel) where "
            "crossing is impossible, what must the driver do?",
            "explanation": "Make sure the passage is clear before entering and give "
            "way per the signs; on rivers priority goes to the down-bound vessel "
            "(going with the current)."},
     "choices": [
         {"fr": "S'assurer que le passage est libre avant de s'engager", "en": "Make "
          "sure the passage is clear before entering", "correct": True},
         {"fr": "S'engager toujours en premier", "en": "Always enter first",
          "correct": False},
         {"fr": "Accélérer pour forcer le passage", "en": "Speed up to force through",
          "correct": False}]},

    # --- Sécurité (fluvial) ------------------------------------------------
    {"option": "eaux_interieures", "theme": "securite", "source": "division_245",
     "ref": "Arrêté du 10 février 2016 (Division 245), art. 5 — EIF par personne (eaux intérieures)",
     "polarity": "affirmative",
     "fr": {"stem": "À bord d'une menue embarcation en eaux intérieures, de quoi "
            "chaque personne doit-elle disposer ?",
            "explanation": "Chaque personne embarquée doit disposer d'un équipement "
            "individuel de flottabilité (brassière / gilet) adapté."},
     "en": {"stem": "Aboard a small craft on inland waters, what must each person have?",
            "explanation": "Every person aboard must have a suitable personal flotation "
            "device (lifejacket / buoyancy aid)."},
     "choices": [
         {"fr": "Un équipement individuel de flottabilité", "en": "A personal flotation "
          "device", "correct": True},
         {"fr": "Une combinaison étanche obligatoire", "en": "A compulsory drysuit",
          "correct": False},
         {"fr": "Rien s'il sait nager", "en": "Nothing, if they can swim",
          "correct": False}]},

    {"option": "eaux_interieures", "theme": "securite", "source": "rgp",
     "ref": "RGP, art. A.4241-47-1 — marque d'identification du bateau", "polarity": "affirmative",
     "fr": {"stem": "La marque d'identification (immatriculation) d'un bateau doit "
            "être :",
            "explanation": "Elle doit être apposée de manière apparente et lisible sur "
            "la coque, pour permettre d'identifier le bateau."},
     "en": {"stem": "A vessel's identification mark (registration) must be:",
            "explanation": "It must be displayed visibly and legibly on the hull, so "
            "the vessel can be identified."},
     "choices": [
         {"fr": "Apposée visiblement et lisiblement sur la coque", "en": "Displayed "
          "visibly and legibly on the hull", "correct": True},
         {"fr": "Conservée uniquement dans les papiers du bord", "en": "Kept only in "
          "the boat's papers", "correct": False},
         {"fr": "Facultative pour la plaisance", "en": "Optional for pleasure craft",
          "correct": False}]},

    {"option": "eaux_interieures", "theme": "securite", "source": "rgp",
     "ref": "RGP, art. R.4241-9/-10 — devoir général de prudence du conducteur", "polarity": "affirmative",
     "fr": {"stem": "Avant d'appareiller, que doit notamment vérifier le chef de bord "
            "(devoir de vigilance) ?",
            "explanation": "Il s'assure du bon état du bateau et du moteur, de la "
            "présence du matériel de sécurité et des conditions (niveau d'eau, météo)."},
     "en": {"stem": "Before getting under way, what must the skipper check (duty of "
            "care)?",
            "explanation": "Ensure the boat and engine are sound, the safety equipment "
            "is aboard, and the conditions (water level, weather) are suitable."},
     "choices": [
         {"fr": "L'état du bateau, le matériel de sécurité et la météo", "en": "The "
          "boat's condition, the safety gear and the weather", "correct": True},
         {"fr": "Uniquement le niveau de carburant", "en": "Only the fuel level",
          "correct": False},
         {"fr": "Rien, la vérification incombe à l'écluse", "en": "Nothing — checks are "
          "the lock's job", "correct": False}]},

    # --- Réglementation (fluvial) ------------------------------------------
    {"option": "eaux_interieures", "theme": "reglementation", "source": "decret_2007",
     "ref": "Décret n° 2007-1167 du 2 août 2007, art. 2 — option eaux intérieures", "polarity": "affirmative",
     "fr": {"stem": "Quel titre faut-il pour conduire un bateau de plaisance à moteur "
            "de plus de 4,5 kW sur les rivières et canaux ?",
            "explanation": "Il faut le permis plaisance option « eaux intérieures » "
            "(l'option côtière, elle, vaut pour la mer)."},
     "en": {"stem": "What licence is needed to drive a motor pleasure boat over 4.5 kW "
            "on rivers and canals?",
            "explanation": "The permis plaisance “eaux intérieures” option "
            "(the côtière option is for the sea)."},
     "choices": [
         {"fr": "Le permis plaisance option eaux intérieures", "en": "The permis "
          "plaisance inland-waters option", "correct": True},
         {"fr": "Aucun titre n'est nécessaire", "en": "No licence is needed",
          "correct": False},
         {"fr": "L'option côtière suffit toujours", "en": "The côtière option always "
          "suffices", "correct": False}]},

    {"option": "eaux_interieures", "theme": "reglementation", "source": "rgp",
     "ref": "Code des transports, art. R.4241-31/-32 — règlement particulier de police (RPP)", "polarity": "affirmative",
     "fr": {"stem": "Outre le règlement général de police (RGP), une voie d'eau "
            "particulière peut être encadrée par :",
            "explanation": "Un règlement particulier de police (RPP) adapte les règles "
            "générales aux circonstances locales d'une voie ou d'un bief donné."},
     "en": {"stem": "Besides the general police regulation (RGP), a particular waterway "
            "may also be governed by:",
            "explanation": "A particular police regulation (RPP) adapts the general "
            "rules to the local circumstances of a given waterway or reach."},
     "choices": [
         {"fr": "Un règlement particulier de police (RPP)", "en": "A particular police "
          "regulation (RPP)", "correct": True},
         {"fr": "Le seul code de la route", "en": "The road traffic code alone",
          "correct": False},
         {"fr": "Aucune autre règle", "en": "No other rule", "correct": False}]},

    {"option": "eaux_interieures", "theme": "reglementation", "source": "code_transports",
     "ref": "Code des transports, art. L.4274-14 — conduite en état alcoolique (≥ 0,5 g/L)", "polarity": "affirmative",
     "fr": {"stem": "La conduite d'un bateau sous l'emprise d'un état alcoolique est :",
            "explanation": "Elle est interdite : le chef de bord doit être en état de "
            "gouverner et de réagir, comme pour la conduite d'un véhicule."},
     "en": {"stem": "Driving a boat under the influence of alcohol is:",
            "explanation": "Prohibited: the skipper must be fit to steer and react, "
            "as when driving a vehicle."},
     "choices": [
         {"fr": "Interdite", "en": "Prohibited", "correct": True},
         {"fr": "Autorisée sur les canaux", "en": "Allowed on canals", "correct": False},
         {"fr": "Tolérée la nuit", "en": "Tolerated at night", "correct": False}]},

    # --- Environnement (fluvial) -------------------------------------------
    {"option": "eaux_interieures", "theme": "environnement", "source": "rgp",
     "ref": "RGP (Code des transports, art. R.4241-62) — rejet d'hydrocarbures interdit", "polarity": "affirmative",
     "fr": {"stem": "En eaux intérieures, le rejet d'hydrocarbures, d'eaux usées ou "
            "de détritus dans la voie d'eau est :",
            "explanation": "Il est interdit : ces rejets polluent la voie d'eau et "
            "doivent être collectés et déposés dans les installations prévues."},
     "en": {"stem": "On inland waters, discharging hydrocarbons, waste water or rubbish "
            "into the waterway is:",
            "explanation": "Prohibited: such discharges pollute the waterway and must "
            "be collected and disposed of in the proper facilities."},
     "choices": [
         {"fr": "Interdit", "en": "Prohibited", "correct": True},
         {"fr": "Autorisé en faible quantité", "en": "Allowed in small amounts",
          "correct": False},
         {"fr": "Libre en dehors des ports", "en": "Free outside harbours",
          "correct": False}]},

    {"option": "eaux_interieures", "theme": "environnement", "source": "rgp",
     "ref": "RGP, art. A.4241-53-21 — réduire vitesse et batillage près des berges", "polarity": "affirmative",
     "fr": {"stem": "Pour limiter l'érosion des berges et le dérangement de la faune, "
            "le plaisancier doit surtout :",
            "explanation": "Réduire sa vitesse et son batillage à l'approche des rives, "
            "des roselières et des zones naturelles sensibles."},
     "en": {"stem": "To limit bank erosion and disturbance to wildlife, the boater "
            "should above all:",
            "explanation": "Reduce speed and wash when approaching banks, reed beds and "
            "sensitive natural areas."},
     "choices": [
         {"fr": "Réduire sa vitesse et son batillage près des rives", "en": "Reduce "
          "speed and wash near the banks", "correct": True},
         {"fr": "Naviguer à pleine vitesse au centre", "en": "Run at full speed in the "
          "centre", "correct": False},
         {"fr": "S'amarrer dans les roselières", "en": "Moor in the reed beds",
          "correct": False}]},

    # --- Compléments option eaux intérieures (banque portée à 40) ----------
    # Voies navigables et stationnement
    {"option": "eaux_interieures", "theme": "voies_navigables", "source": "rgp",
     "ref": "RGP, art. A.4241-53-1 et -53-6 §2 — montant/avalant (priorité à l'avalant)", "polarity": "affirmative",
     "fr": {"stem": "En navigation intérieure, que désigne un bateau « avalant » ?",
            "explanation": "Un avalant descend le courant (il va vers l'aval) ; un "
            "montant le remonte. Sur les rivières, l'avalant, moins manœuvrant, est "
            "prioritaire."},
     "en": {"stem": "On inland waters, what is a “down-bound” (avalant) vessel?",
            "explanation": "A down-bound vessel goes with the current (downstream); an "
            "up-bound (montant) one goes against it. On rivers the down-bound vessel, "
            "less manoeuvrable, has priority."},
     "choices": [
         {"fr": "Un bateau qui descend le courant", "en": "A vessel going downstream",
          "correct": True},
         {"fr": "Un bateau qui remonte le courant", "en": "A vessel going upstream",
          "correct": False},
         {"fr": "Un bateau à l'arrêt contre la berge", "en": "A vessel stopped against "
          "the bank", "correct": False}]},

    {"option": "eaux_interieures", "theme": "voies_navigables", "source": "rgp",
     "ref": "Voie navigable — repérage par points kilométriques (PK)", "polarity": "affirmative",
     "fr": {"stem": "Le long d'un fleuve ou d'un canal, comment repère-t-on sa "
            "position ?",
            "explanation": "Par les points kilométriques (PK), matérialisés par des "
            "bornes ou plaques sur les rives, qui comptent les kilomètres depuis "
            "l'origine de la voie d'eau."},
     "en": {"stem": "Along a river or canal, how is your position located?",
            "explanation": "By kilometre points (PK), shown by markers or plates on the "
            "banks, counting the kilometres from the start of the waterway."},
     "choices": [
         {"fr": "Par les points kilométriques (bornes des rives)", "en": "By kilometre "
          "points (bank markers)", "correct": True},
         {"fr": "Par la latitude et la longitude seules", "en": "By latitude and "
          "longitude alone", "correct": False},
         {"fr": "Par les milles nautiques", "en": "By nautical miles", "correct": False}]},

    {"option": "eaux_interieures", "theme": "voies_navigables", "source": "rgp",
     "ref": "RGP, annexe 5, panneau C.2 — hauteur libre limitée (tirant d'air)", "polarity": "affirmative",
     "fr": {"stem": "Avant de passer sous un pont ou une ligne électrique, que doit "
            "vérifier le conducteur ?",
            "explanation": "Que son tirant d'air (hauteur du bateau au-dessus de l'eau) "
            "est inférieur à la hauteur libre disponible, indiquée par la signalisation."},
     "en": {"stem": "Before passing under a bridge or a power line, what must the "
            "driver check?",
            "explanation": "That the air draft (the boat's height above the water) is "
            "less than the available headroom, shown by the signs."},
     "choices": [
         {"fr": "Que son tirant d'air est inférieur à la hauteur libre", "en": "That the "
          "air draft is less than the available headroom", "correct": True},
         {"fr": "Que sa vitesse est maximale", "en": "That its speed is at maximum",
          "correct": False},
         {"fr": "Que son ancre est mouillée", "en": "That its anchor is down",
          "correct": False}]},

    # Écluses, barrages et ouvrages
    {"option": "eaux_interieures", "theme": "ecluses", "source": "rgp",
     "ref": "RGP, art. A.4241-53-31 §4 et §12 — instructions de l'éclusier", "polarity": "affirmative",
     "fr": {"stem": "À l'écluse, qui fixe l'ordre et les modalités d'entrée des "
            "bateaux ?",
            "explanation": "L'éclusier (ou la signalisation / l'automatisme de "
            "l'écluse) ; on suit ses instructions et les feux."},
     "en": {"stem": "At a lock, who sets the order and manner in which vessels enter?",
            "explanation": "The lock-keeper (or the lock's signs / automatic system); "
            "follow their instructions and the lights."},
     "choices": [
         {"fr": "L'éclusier et la signalisation de l'écluse", "en": "The lock-keeper and "
          "the lock's signs", "correct": True},
         {"fr": "Le bateau le plus rapide", "en": "The fastest vessel", "correct": False},
         {"fr": "Chaque conducteur, librement", "en": "Each driver, freely",
          "correct": False}]},

    {"option": "eaux_interieures", "theme": "ecluses", "source": "rgp",
     "ref": "RGP, art. A.4241-53-31 §1(a) — deux feux rouges (écluse hors service)", "polarity": "affirmative",
     "fr": {"stem": "À une écluse, que signifient DEUX feux rouges ?",
            "explanation": "L'écluse est hors service / fermée à la navigation. Un seul "
            "feu rouge signifie « attendez » et le feu vert autorise l'entrée."},
     "en": {"stem": "At a lock, what do TWO red lights mean?",
            "explanation": "The lock is out of service / closed to navigation. A single "
            "red light means “wait”, and a green light authorises entry."},
     "choices": [
         {"fr": "L'écluse est hors service", "en": "The lock is out of service",
          "correct": True},
         {"fr": "L'entrée est immédiatement autorisée", "en": "Entry is immediately "
          "authorised", "correct": False},
         {"fr": "La sortie est obligatoire", "en": "Exit is compulsory", "correct": False}]},

    # Signalisation des voies et des bateaux
    {"option": "eaux_interieures", "theme": "signalisation_fluviale", "source": "rgp",
     "ref": "RGP, annexe 5, section A — signaux d'interdiction (bord rouge)", "polarity": "affirmative",
     "fr": {"stem": "En navigation intérieure, à quoi reconnaît-on un panneau "
            "d'INTERDICTION ?",
            "explanation": "Les panneaux d'interdiction ont un bord rouge (souvent une "
            "bande blanche barrée de rouge), comme le panneau « passage interdit »."},
     "en": {"stem": "On inland waters, how do you recognise a PROHIBITION sign?",
            "explanation": "Prohibition signs have a red border (often a white bar with "
            "red), like the “no entry” sign."},
     "choices": [
         {"fr": "À son bord rouge", "en": "By its red border", "correct": True},
         {"fr": "À sa couleur entièrement bleue", "en": "By being entirely blue",
          "correct": False},
         {"fr": "À sa forme triangulaire verte", "en": "By a green triangular shape",
          "correct": False}]},

    {"option": "eaux_interieures", "theme": "signalisation_fluviale", "source": "rgp",
     "ref": "RGP, annexe 5, section E — signaux d'indication (bleus)", "polarity": "affirmative",
     "fr": {"stem": "Que donne, en règle générale, un panneau rectangulaire BLEU à "
            "symbole blanc ?",
            "explanation": "Les panneaux bleus rectangulaires donnent une indication ou "
            "un renseignement (stationnement autorisé, bac, point de service…)."},
     "en": {"stem": "What does a rectangular BLUE sign with a white symbol generally "
            "give?",
            "explanation": "Blue rectangular signs give information (mooring allowed, "
            "ferry, service point, etc.)."},
     "choices": [
         {"fr": "Une indication / un renseignement", "en": "Information / guidance",
          "correct": True},
         {"fr": "Une interdiction absolue", "en": "An absolute prohibition",
          "correct": False},
         {"fr": "Un danger immédiat", "en": "An immediate danger", "correct": False}]},

    {"option": "eaux_interieures", "theme": "signalisation_fluviale", "source": "rgp",
     "ref": "RGP, annexe 5, panneau E.5 — stationnement autorisé (P)", "polarity": "affirmative",
     "fr": {"stem": "Un panneau carré BLEU portant la lettre « P » blanche signifie :",
            "explanation": "Stationnement (amarrage) autorisé à cet endroit."},
     "en": {"stem": "A square BLUE sign bearing a white letter “P” means:",
            "explanation": "Mooring (berthing) is permitted at this spot."},
     "choices": [
         {"fr": "Stationnement autorisé", "en": "Mooring permitted", "correct": True},
         {"fr": "Stationnement interdit", "en": "Mooring prohibited", "correct": False},
         {"fr": "Port de plaisance à 1 km", "en": "Marina 1 km ahead", "correct": False}]},

    {"option": "eaux_interieures", "theme": "signalisation_fluviale", "source": "rgp",
     "ref": "RGP, annexe 5, panneau B.1 — obligation (suivre la flèche)", "polarity": "affirmative",
     "fr": {"stem": "Un panneau à bord rouge portant une flèche blanche indique :",
            "explanation": "C'est un panneau d'obligation : il impose de suivre la "
            "direction (le côté) indiquée par la flèche."},
     "en": {"stem": "A red-bordered sign bearing a white arrow indicates:",
            "explanation": "It is a mandatory sign: you must follow the direction (the "
            "side) shown by the arrow."},
     "choices": [
         {"fr": "Une obligation de suivre la direction indiquée", "en": "An obligation "
          "to follow the shown direction", "correct": True},
         {"fr": "Une simple recommandation", "en": "A mere recommendation",
          "correct": False},
         {"fr": "Une zone de baignade", "en": "A bathing area", "correct": False}]},

    {"option": "eaux_interieures", "theme": "signalisation_fluviale", "source": "rgp",
     "ref": "RGP, annexe 5, section C — restriction (hauteur, largeur ou profondeur)", "polarity": "affirmative",
     "fr": {"stem": "Un panneau portant un nombre (par ex. « 3,50 m ») signale "
            "généralement :",
            "explanation": "Une limitation (restriction) : par exemple la hauteur libre, "
            "la largeur ou la profondeur disponible (panneaux série C). Une vitesse maximale relève, elle, d'un panneau d'obligation (B.6)."},
     "en": {"stem": "A sign bearing a number (e.g. “3.50 m”) generally indicates:",
            "explanation": "A restriction: for example the available headroom, width or "
            "depth (series C signs). A maximum speed is instead a mandatory sign (B.6)."},
     "choices": [
         {"fr": "Une limitation de hauteur, de largeur ou de profondeur", "en": "A "
          "limit on headroom, width or depth", "correct": True},
         {"fr": "La distance jusqu'à la prochaine écluse", "en": "The distance to the "
          "next lock", "correct": False},
         {"fr": "Le numéro de la voie d'eau", "en": "The waterway's number",
          "correct": False}]},

    # Règles de route (fluvial)
    {"option": "eaux_interieures", "theme": "regles_route", "source": "rgp",
     "ref": "RGP, art. A.4241-53-6 §2 — priorité de l'avalant", "polarity": "affirmative",
     "fr": {"stem": "Sur une rivière à courant, lorsqu'un montant et un avalant se "
            "rencontrent, qui est prioritaire ?",
            "explanation": "L'avalant (qui descend le courant) est prioritaire car il "
            "manœuvre moins bien ; le montant lui laisse la route et le bord voulu."},
     "en": {"stem": "On a flowing river, when an up-bound and a down-bound vessel meet, "
            "which has priority?",
            "explanation": "The down-bound vessel (going with the current) has priority "
            "because it manoeuvres less easily; the up-bound vessel leaves it the way "
            "and the chosen side."},
     "choices": [
         {"fr": "L'avalant (qui descend le courant)", "en": "The down-bound vessel",
          "correct": True},
         {"fr": "Le montant (qui remonte le courant)", "en": "The up-bound vessel",
          "correct": False},
         {"fr": "Le plus grand des deux bateaux", "en": "The larger of the two vessels",
          "correct": False}]},

    {"option": "eaux_interieures", "theme": "regles_route", "source": "rgp",
     "ref": "RGP, art. A.4241-53-6 §1 — rencontre (chacun sur tribord)", "polarity": "affirmative",
     "fr": {"stem": "Sur un plan d'eau sans courant, deux bateaux à moteur se "
            "rencontrent face à face. Que font-ils ?",
            "explanation": "Chacun vient sur tribord (sa droite) pour se croiser bâbord "
            "sur bâbord."},
     "en": {"stem": "On still water, two power-driven vessels meet head-on. What do "
            "they do?",
            "explanation": "Each alters to starboard (its right) so they pass port to "
            "port."},
     "choices": [
         {"fr": "Chacun vient sur tribord", "en": "Each alters to starboard",
          "correct": True},
         {"fr": "Chacun vient sur bâbord", "en": "Each alters to port", "correct": False},
         {"fr": "Ils s'arrêtent tous les deux", "en": "They both stop", "correct": False}]},

    {"option": "eaux_interieures", "theme": "regles_route", "source": "rgp",
     "ref": "RGP, art. A.4241-53-11 §1 — dépassement par bâbord", "polarity": "affirmative",
     "fr": {"stem": "En navigation intérieure, de quel côté un bateau en dépasse-t-il "
            "normalement un autre ?",
            "explanation": "En principe par bâbord (la gauche) du bateau rattrapé, après "
            "s'être assuré que la manœuvre est sans danger ; le rattrapant s'écarte du "
            "rattrapé."},
     "en": {"stem": "On inland waters, on which side does a vessel normally overtake "
            "another?",
            "explanation": "As a rule on the port (left) side of the vessel being "
            "overtaken, once sure the manoeuvre is safe; the overtaking vessel keeps "
            "clear of the one overtaken."},
     "choices": [
         {"fr": "Par bâbord (à gauche) du bateau rattrapé", "en": "On the port (left) "
          "side of the overtaken vessel", "correct": True},
         {"fr": "Toujours par tribord", "en": "Always on the starboard side",
          "correct": False},
         {"fr": "En le serrant de très près", "en": "By passing very close to it",
          "correct": False}]},

    # Sécurité (fluvial)
    {"option": "eaux_interieures", "theme": "securite", "source": "division_245",
     "ref": "Arrêté du 10 février 2016 (Division 245), art. 5 — dispositif d'assèchement", "polarity": "affirmative",
     "fr": {"stem": "Parmi le matériel utile à bord d'une menue embarcation, on doit "
            "disposer d'un moyen permettant :",
            "explanation": "D'assécher le bateau (écope, pompe ou seau) en cas d'entrée "
            "d'eau, en plus des équipements individuels de flottabilité."},
     "en": {"stem": "Among the useful equipment aboard a small craft, you must have a "
            "means of:",
            "explanation": "Bailing the boat out (scoop, pump or bucket) if water comes "
            "in, in addition to the personal flotation devices."},
     "choices": [
         {"fr": "D'assécher le bateau (écope ou pompe)", "en": "Bailing the boat out "
          "(scoop or pump)", "correct": True},
         {"fr": "De mesurer la profondeur du chenal", "en": "Measuring the channel "
          "depth", "correct": False},
         {"fr": "De recharger la VHF", "en": "Recharging the VHF", "correct": False}]},

    {"option": "eaux_interieures", "theme": "securite", "source": "division_245",
     "ref": "Arrêté du 10 février 2016 (Division 245), art. 6 — ligne de mouillage", "polarity": "affirmative",
     "fr": {"stem": "Pour pouvoir s'arrêter en sécurité à l'écart d'un quai, une "
            "embarcation doit disposer :",
            "explanation": "D'un moyen de mouillage adapté (une ancre avec sa ligne) "
            "permettant de tenir le bateau."},
     "en": {"stem": "To be able to stop safely away from a quay, a craft must have:",
            "explanation": "A suitable means of anchoring (an anchor with its line) to "
            "hold the boat."},
     "choices": [
         {"fr": "Une ancre avec sa ligne de mouillage", "en": "An anchor with its rode",
          "correct": True},
         {"fr": "Un second moteur", "en": "A second engine", "correct": False},
         {"fr": "Un radeau de survie", "en": "A liferaft", "correct": False}]},

    # Réglementation (fluvial)
    {"option": "eaux_interieures", "theme": "reglementation", "source": "code_transports",
     "ref": "Code des transports, art. L.4221-1 — titre de navigation (carte de circulation)", "polarity": "affirmative",
     "fr": {"stem": "Quel document, propre au bateau, doit pouvoir être présenté à "
            "bord en eaux intérieures ?",
            "explanation": "La carte de circulation (titre de navigation) du bateau, "
            "avec, selon le cas, le permis du conducteur et l'attestation d'assurance."},
     "en": {"stem": "Which document, specific to the boat, must be available aboard on "
            "inland waters?",
            "explanation": "The boat's circulation card (navigation title), together "
            "with, where applicable, the driver's licence and proof of insurance."},
     "choices": [
         {"fr": "La carte de circulation du bateau", "en": "The boat's circulation card",
          "correct": True},
         {"fr": "Une carte routière de la région", "en": "A road map of the area",
          "correct": False},
         {"fr": "Le manuel du moteur uniquement", "en": "Only the engine manual",
          "correct": False}]},

    {"option": "eaux_interieures", "theme": "reglementation", "source": "itu_rr",
     "ref": "UIT, Règlement des radiocommunications, art. 47 — certificat d'opérateur (CRR, délivré par l'ANFR)", "polarity": "affirmative",
     "fr": {"stem": "Pour utiliser une station radio VHF à bord, le chef de bord doit "
            "en principe être titulaire :",
            "explanation": "Du certificat restreint de radiotéléphoniste (CRR), qui "
            "autorise l'emploi d'une VHF. Depuis 2011, il n'est plus exigé en eaux territoriales françaises pour une VHF portative sans ASN ; il reste requis pour une VHF fixe ou à ASN et pour la navigation à l'étranger."},
     "en": {"stem": "To use a VHF radio aboard, the skipper must, as a rule, hold:",
            "explanation": "The restricted radiotelephone certificate (CRR), which "
            "authorises the use of a VHF. Since 2011 it is no longer required in French territorial waters for a hand-held VHF without DSC; it remains required for a fixed or DSC-equipped VHF and for navigating abroad."},
     "choices": [
         {"fr": "Du certificat restreint de radiotéléphoniste (CRR)", "en": "The "
          "restricted radiotelephone certificate (CRR)", "correct": True},
         {"fr": "Du seul permis plaisance", "en": "The boat licence alone",
          "correct": False},
         {"fr": "D'aucun titre particulier", "en": "No particular certificate",
          "correct": False}]},

    # Environnement (fluvial)
    {"option": "eaux_interieures", "theme": "environnement", "source": "code_transports",
     "ref": "Code des transports, art. R.4241-63 / CDNI (décret 2010-197) — eaux usées (cuve, dépôt à terre)", "polarity": "affirmative",
     "fr": {"stem": "Que doit faire le plaisancier de ses eaux usées (eaux noires) en "
            "eaux intérieures ?",
            "explanation": "Les conserver dans une cuve à bord puis les vider dans les "
            "installations de collecte à terre ; leur rejet dans la voie d'eau est "
            "interdit."},
     "en": {"stem": "What should the boater do with waste water (black water) on inland "
            "waters?",
            "explanation": "Keep it in a holding tank aboard, then empty it at shore "
            "collection facilities; discharging it into the waterway is prohibited."},
     "choices": [
         {"fr": "Les stocker en cuve et les vider à terre", "en": "Hold it in a tank and "
          "empty it ashore", "correct": True},
         {"fr": "Les rejeter discrètement la nuit", "en": "Discharge it discreetly at "
          "night", "correct": False},
         {"fr": "Les rejeter loin des berges", "en": "Discharge it far from the banks",
          "correct": False}]},

    {"option": "eaux_interieures", "theme": "environnement", "source": "rgp",
     "ref": "RGP (Code des transports, art. R.4241-62) — prévention de la pollution", "polarity": "affirmative",
     "fr": {"stem": "Lors du plein de carburant, quelle précaution évite la pollution "
            "de l'eau ?",
            "explanation": "Faire le plein sans précipitation et sans remplir à ras "
            "bord (entonnoir, surveillance du niveau) pour éviter tout débordement "
            "d'hydrocarbures à l'eau."},
     "en": {"stem": "When refuelling, what precaution prevents water pollution?",
            "explanation": "Refuel unhurriedly and do not fill to the brim (use a "
            "funnel, watch the level) to avoid any fuel spilling into the water."},
     "choices": [
         {"fr": "Éviter tout débordement (ne pas remplir à ras bord)", "en": "Avoid any "
          "overflow (do not fill to the brim)", "correct": True},
         {"fr": "Remplir le plus vite possible", "en": "Fill as fast as possible",
          "correct": False},
         {"fr": "Rincer le réservoir à l'eau du canal", "en": "Rinse the tank with canal "
          "water", "correct": False}]},
]
