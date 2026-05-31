"use strict";
/* UI translations for the player. The four languages match the project scope:
 * FR/DE/IT have officially-published Swiss law to ground questions against; EN
 * has no official legal text, so English content (when present) is a clearly
 * labelled *unofficial study translation*. These tables cover the UI chrome
 * only — question text comes from the per-language questions.<lang>.json bank,
 * falling back to French where a language's bank isn't built yet. */

const LANGS = ["fr", "de", "it", "en"];
const DEFAULT_LANG = "fr";

const LANG_NAMES = { fr: "Français", de: "Deutsch", it: "Italiano", en: "English" };

const THEME_LABELS = {
  fr: {
    definitions: "Définitions",
    meteorologie: "Météorologie",
    lois: "Lois sur la navigation",
    signalisation: "Signalisation et signaux acoustiques",
    matelotage: "Matelotage",
    eaux_frontalieres: "Eaux frontalières",
    voile: "Navigation à voile",
    // France — permis plaisance (côtière + eaux intérieures)
    securite: "Sécurité et matériel d'armement",
    balisage: "Balisage et signalisation maritime",
    regles_route: "Règles de barre et de route",
    feux_signaux: "Feux, marques et signaux",
    meteo_maree: "Météorologie et marées",
    reglementation: "Réglementation, permis et radio",
    environnement: "Protection de l'environnement",
    voies_navigables: "Voies navigables et stationnement",
    ecluses: "Écluses, barrages et ouvrages",
    signalisation_fluviale: "Signalisation des voies et des bateaux",
    // Germany — Sportbootführerschein (its own taxonomy). Listed here, in exam
    // order, because DEFAULT_LANG (fr) keys define the domain display order; the
    // labels actually shown come from the `de` map below (the DE bundle is
    // German-only). Distinct ids, so the Swiss/French banks are unaffected.
    definitionen: "Begriffsbestimmungen",
    verkehrsregeln: "Verkehrs- und Fahrregeln",
    schifffahrtszeichen: "Schifffahrtszeichen",
    lichter_signale: "Lichter und Signale",
    wetterkunde: "Wetterkunde",
    seemannschaft: "Seemannschaft",
    navigation: "Navigation",
    gezeiten: "Gezeiten und Strömung",
    umweltschutz: "Umweltschutz",
    recht_dokumente: "Recht und Dokumente",
  },
  de: {
    definitions: "Begriffe",
    meteorologie: "Meteorologie",
    lois: "Schifffahrtsrecht",
    signalisation: "Signale und Schallzeichen",
    matelotage: "Seemannschaft",
    eaux_frontalieres: "Grenzgewässer",
    voile: "Segeln",
    // Germany — Sportbootführerschein taxonomy (shown in the web/de/ player).
    definitionen: "Begriffsbestimmungen",
    verkehrsregeln: "Verkehrs- und Fahrregeln",
    schifffahrtszeichen: "Schifffahrtszeichen",
    lichter_signale: "Lichter und Signale",
    wetterkunde: "Wetterkunde",
    seemannschaft: "Seemannschaft",
    navigation: "Navigation",
    gezeiten: "Gezeiten und Strömung",
    umweltschutz: "Umweltschutz",
    recht_dokumente: "Recht und Dokumente",
  },
  it: {
    definitions: "Definizioni",
    meteorologie: "Meteorologia",
    lois: "Norme di navigazione",
    signalisation: "Segnaletica e segnali acustici",
    matelotage: "Marineria",
    eaux_frontalieres: "Acque di confine",
    voile: "Navigazione a vela",
  },
  en: {
    definitions: "Definitions",
    meteorologie: "Meteorology",
    lois: "Navigation law",
    signalisation: "Signs and sound signals",
    matelotage: "Seamanship",
    eaux_frontalieres: "Border waters",
    voile: "Sailing",
    // France — permis plaisance (coastal + inland-waters)
    securite: "Safety and required equipment",
    balisage: "Maritime buoyage and marks",
    regles_route: "Steering and sailing rules",
    feux_signaux: "Lights, shapes and signals",
    meteo_maree: "Weather and tides",
    reglementation: "Regulations, licence and radio",
    environnement: "Environmental protection",
    voies_navigables: "Waterways and mooring",
    ecluses: "Locks, dams and structures",
    signalisation_fluviale: "Waterway and vessel signs",
    // International / harmonised — COLREG 1972 (the INT player)
    general: "General (application, definitions)",
    steering_sailing: "Steering and sailing rules",
    lights_shapes: "Lights and shapes",
    sound_light_signals: "Sound and light signals",
    exemptions: "Exemptions",
    annexes: "Technical annexes",
  },
};

const STRINGS = {
  fr: {
    pageTitle: "Permis bateau Léman — examen théorique (entraînement)",
    h1: "Permis bateau — examen théorique",
    subtitle: "Catégorie A (bateau à moteur) · Lac Léman",
    demoBanner:
      "<strong>Banque en construction.</strong> Les six thèmes sont désormais " +
      "couverts, mais la <em>signalisation</em> reste sur-représentée par rapport à " +
      "l’examen réel. Les questions sont dérivées de sources libres (droit fédéral " +
      "ONI/RNL et références sous licence ouverte) : ce n’est pas un examen blanc " +
      "officiel, et la banque continue de s’étoffer.",
    fallbackBanner:
      "Questions affichées en français — la traduction {lang} est en cours de constitution.",
    unofficialBanner:
      "Traduction d’étude non officielle. Le droit suisse n’est pas publié en anglais ; " +
      "seules les versions FR/DE/IT font foi.",
    cfgQuestions: "Questions",
    cfgDuration: "Durée",
    cfgSuccess: "Réussite",
    cfgScale: "Barème",
    cfgAvailable: "Disponibles",
    cfgPartial: "(sur {target} visés — banque en cours de constitution)",
    minUnit: "min",
    points: "points",
    ptsPerQuestion: "{n} pts/question",
    availableQuestions: "{n} questions",
    btnExam: "Examen blanc (chronométré)",
    btnPractice: "Entraînement libre",
    btnRestart: "Recommencer",
    btnValidate: "Valider",
    btnNext: "Suivante",
    btnFinish: "Terminer",
    btnSeeResult: "Voir le résultat",
    sourceNote:
      "Source : ordonnances fédérales (domaine public). Aucune question issue " +
      "d’une banque sous licence.",
    progress: "Question {i} / {n}",
    multiHint: "Une ou deux réponses peuvent être correctes.",
    kbdHint: "Touches 1-3 pour (dé)cocher · Entrée pour valider.",
    altSignal: "signal à identifier",
    resultTitle: "Résultat",
    detailedCorrection: "Correction détaillée",
    passed: "Réussi",
    failed: "Échoué",
    scoreLine: "{earned} / {total} points (seuil {pass})",
    faultPoints: "Points de faute :",
    duration: "Durée :",
    partialExam:
      "Examen partiel : {n} questions disponibles sur {target}. Score indicatif.",
    yourChoice: "(votre choix)",
    sourceLabel: "Source",
    stateOf: "(état {date})",
    figureTag: "[figure]",
    footTagline: "Outil d’étude libre · construit à partir de sources primaires de droit",
    chooseDomains: "Réviser par domaine :",
    chooseCanton: "Canton (durée de l’examen) :",
    choosePermit: "Permis (épreuve) :",
    cfgPermit: "Permis",
    studyOnly: "Thème d’étude (épreuve pratique) — hors examen théorique.",
    permit_A: "Permis A — bateau à moteur",
    permit_D: "Permis D — voile",
    permitNote_A: "Bateau à moteur dont la puissance dépasse 6 kW " +
      "(4,4 kW sur le lac de Constance).",
    permitNote_D: "Bateau à voile dont la surface vélique dépasse 15 m² " +
      "(12 m² sur le lac de Constance). Examen théorique identique au permis A ; " +
      "seule l’épreuve pratique diffère.",
    scoreLineCount: "{correct} / {total} bonnes réponses",
    blkMin: "(min. {n})",
    blk_basis: "Questions de base",
    blk_spezifisch_binnen: "Spécifique eaux intérieures",
    blk_spezifisch_see: "Spécifique mer",
    blk_segeln: "Spécifique voile",
    blk_navigation: "Navigation",
    poolLabel: "Banque de questions :",
    poolNational: "Banque nationale",
    poolCore: "Tronc commun",
    poolHint: "Le tronc commun ne retient que les questions portables : matelotage " +
      "universel et code de navigation harmonisé (CEVNI sur les eaux intérieures, " +
      "COLREG/RIPAM en mer). La banque nationale ajoute le droit propre au pays.",
    domainAll: "Tout sélectionner",
    domainNone: "Tout désélectionner",
    byDomain: "Score par domaine",
    ankiTitle: "Réviser hors-ligne avec Anki :",
    ankiApkg: "Paquet Anki (.apkg, {n} cartes)",
    ankiTsv: "Tableau éditable (.tsv)",
    giftBtn: "Moodle (GIFT)",
    ankiHint: "Importez le .apkg dans Anki (ordinateur/mobile) ou le .gift dans Moodle. Le .tsv permet de proposer des corrections.",
    loadError:
      "<b>Impossible de charger les questions.</b> Lancez d’abord " +
      "<code>python run.py questions &amp;&amp; python run.py web</code>, puis servez le dossier.",
  },
  de: {
    pageTitle: "Bootsprüfung Genfersee — Theorieprüfung (Übung)",
    h1: "Bootsprüfung — Theorieprüfung",
    subtitle: "Kategorie A (Motorboot) · Genfersee",
    demoBanner:
      "<strong>Fragenkatalog im Aufbau.</strong> Alle sechs Themen sind nun " +
      "abgedeckt, doch die <em>Signalisation</em> ist gegenüber der echten Prüfung " +
      "noch übervertreten. Die Fragen stammen aus frei nutzbaren Quellen " +
      "(Bundesrecht BSV/SVL und offen lizenzierte Referenzen): Es ist keine " +
      "offizielle Musterprüfung, und der Katalog wächst weiter.",
    fallbackBanner:
      "Fragen werden auf Französisch angezeigt — die {lang}-Übersetzung wird noch erstellt.",
    unofficialBanner:
      "Inoffizielle Lernübersetzung. Das Schweizer Recht wird nicht auf Englisch publiziert; " +
      "verbindlich sind nur die Fassungen FR/DE/IT.",
    cfgQuestions: "Fragen",
    cfgDuration: "Dauer",
    cfgSuccess: "Bestehen",
    cfgScale: "Bewertung",
    cfgAvailable: "Verfügbar",
    cfgPartial: "(von {target} angestrebt — Fragenpool im Aufbau)",
    minUnit: "Min.",
    points: "Punkte",
    ptsPerQuestion: "{n} Pkt./Frage",
    availableQuestions: "{n} Fragen",
    btnExam: "Musterprüfung (mit Zeit)",
    btnPractice: "Freies Üben",
    btnRestart: "Neu starten",
    btnValidate: "Bestätigen",
    btnNext: "Weiter",
    btnFinish: "Abschliessen",
    btnSeeResult: "Ergebnis anzeigen",
    sourceNote:
      "Quelle: eidgenössische Verordnungen (gemeinfrei). Keine Frage aus einer " +
      "lizenzierten Sammlung.",
    progress: "Frage {i} / {n}",
    multiHint: "Eine oder zwei Antworten können richtig sein.",
    kbdHint: "Tasten 1-3 zum An-/Abwählen · Enter zum Bestätigen.",
    altSignal: "zu erkennendes Signal",
    resultTitle: "Ergebnis",
    detailedCorrection: "Detaillierte Auflösung",
    passed: "Bestanden",
    failed: "Nicht bestanden",
    scoreLine: "{earned} / {total} Punkte (Grenze {pass})",
    faultPoints: "Fehlerpunkte:",
    duration: "Dauer:",
    partialExam:
      "Teilprüfung: {n} von {target} Fragen verfügbar. Richtwert.",
    yourChoice: "(Ihre Wahl)",
    sourceLabel: "Quelle",
    stateOf: "(Stand {date})",
    figureTag: "[Abbildung]",
    footTagline: "Freies Lernwerkzeug · aus primären Rechtsquellen aufgebaut",
    chooseDomains: "Nach Themen üben:",
    chooseCanton: "Kanton (Prüfungsdauer):",
    choosePermit: "Führerscheinart:",
    studyOnly: "Lernthema (praktische Prüfung) — nicht in der Theorieprüfung.",
    permit_A: "Kat. A — Motorboot",
    permit_D: "Kat. D — Segelboot",
    permitNote_A: "Motorboot mit einer Leistung über 6 kW " +
      "(4,4 kW auf dem Bodensee).",
    permitNote_D: "Segelboot mit einer Segelfläche über 15 m² " +
      "(12 m² auf dem Bodensee). Theorieprüfung identisch mit Kat. A; " +
      "nur die praktische Prüfung unterscheidet sich.",
    cfgPermit: "Führerschein",
    scoreLineCount: "{correct} / {total} richtig",
    blkMin: "(mind. {n})",
    blk_basis: "Basisfragen",
    blk_spezifisch_binnen: "Spezifische Fragen Binnen",
    blk_spezifisch_see: "Spezifische Fragen See",
    blk_segeln: "Spezifische Fragen Segeln",
    blk_navigation: "Navigationsaufgaben",
    poolLabel: "Fragenpool:",
    poolNational: "Nationaler Pool",
    poolCore: "Gemeinsamer Kern",
    poolHint: "Der gemeinsame Kern enthält nur die übertragbaren Fragen: " +
      "universelle Seemannschaft und der harmonisierte Verkehrscode (CEVNI binnen, " +
      "KVR/COLREG auf See). Der nationale Pool ergänzt das landeseigene Recht.",
    domainAll: "Alle auswählen",
    domainNone: "Alle abwählen",
    byDomain: "Ergebnis nach Thema",
    ankiTitle: "Offline lernen mit Anki:",
    ankiApkg: "Anki-Paket (.apkg, {n} Karten)",
    ankiTsv: "Editierbare Tabelle (.tsv)",
    giftBtn: "Moodle (GIFT)",
    ankiHint: "Importieren Sie das .apkg in Anki (Desktop/Mobil) oder das .gift in Moodle. Mit dem .tsv können Sie Korrekturen vorschlagen.",
    loadError:
      "<b>Fragen konnten nicht geladen werden.</b> Führen Sie zuerst " +
      "<code>python run.py questions &amp;&amp; python run.py web</code> aus und hosten Sie den Ordner.",
  },
  it: {
    pageTitle: "Licenza nautica Lemano — esame teorico (allenamento)",
    h1: "Licenza nautica — esame teorico",
    subtitle: "Categoria A (battello a motore) · Lago Lemano",
    demoBanner:
      "<strong>Banca dati in costruzione.</strong> Tutti e sei i temi sono ora " +
      "coperti, ma la <em>segnaletica</em> resta sovrarappresentata rispetto " +
      "all’esame reale. Le domande derivano da fonti libere (diritto federale " +
      "ONI/RNL e riferimenti con licenza aperta): non è un esame simulato ufficiale " +
      "e la banca dati continua ad ampliarsi.",
    fallbackBanner:
      "Domande mostrate in francese — la traduzione {lang} è in corso di realizzazione.",
    unofficialBanner:
      "Traduzione di studio non ufficiale. Il diritto svizzero non è pubblicato in inglese; " +
      "fanno fede solo le versioni FR/DE/IT.",
    cfgQuestions: "Domande",
    cfgDuration: "Durata",
    cfgSuccess: "Promozione",
    cfgScale: "Punteggio",
    cfgAvailable: "Disponibili",
    cfgPartial: "(su {target} previste — banca in costruzione)",
    minUnit: "min",
    points: "punti",
    ptsPerQuestion: "{n} pti/domanda",
    availableQuestions: "{n} domande",
    btnExam: "Esame simulato (cronometrato)",
    btnPractice: "Allenamento libero",
    btnRestart: "Ricomincia",
    btnValidate: "Conferma",
    btnNext: "Avanti",
    btnFinish: "Termina",
    btnSeeResult: "Vedi il risultato",
    sourceNote:
      "Fonte: ordinanze federali (dominio pubblico). Nessuna domanda tratta da una " +
      "banca sotto licenza.",
    progress: "Domanda {i} / {n}",
    multiHint: "Una o due risposte possono essere corrette.",
    kbdHint: "Tasti 1-3 per (de)selezionare · Invio per validare.",
    altSignal: "segnale da identificare",
    resultTitle: "Risultato",
    detailedCorrection: "Correzione dettagliata",
    passed: "Promosso",
    failed: "Bocciato",
    scoreLine: "{earned} / {total} punti (soglia {pass})",
    faultPoints: "Punti di errore:",
    duration: "Durata:",
    partialExam:
      "Esame parziale: {n} domande disponibili su {target}. Punteggio indicativo.",
    yourChoice: "(la tua scelta)",
    sourceLabel: "Fonte",
    stateOf: "(stato {date})",
    figureTag: "[figura]",
    footTagline: "Strumento di studio libero · costruito da fonti giuridiche primarie",
    chooseDomains: "Ripassa per tema:",
    chooseCanton: "Cantone (durata dell’esame):",
    choosePermit: "Categoria (esame):",
    studyOnly: "Tema di studio (prova pratica) — non nell’esame teorico.",
    permit_A: "Cat. A — barca a motore",
    permit_D: "Cat. D — barca a vela",
    permitNote_A: "Barca a motore di potenza superiore a 6 kW " +
      "(4,4 kW sul Lago di Costanza).",
    permitNote_D: "Barca a vela con superficie velica superiore a 15 m² " +
      "(12 m² sul Lago di Costanza). Esame teorico identico alla cat. A; " +
      "solo la prova pratica è diversa.",
    poolLabel: "Banca delle domande:",
    poolNational: "Banca nazionale",
    poolCore: "Tronco comune",
    poolHint: "Il tronco comune contiene solo le domande portabili: marineria " +
      "universale e il codice di navigazione armonizzato (CEVNI sulle acque interne, " +
      "COLREG/RIPAM in mare). La banca nazionale aggiunge il diritto proprio del paese.",
    domainAll: "Seleziona tutto",
    domainNone: "Deseleziona tutto",
    byDomain: "Punteggio per tema",
    ankiTitle: "Studia offline con Anki:",
    ankiApkg: "Pacchetto Anki (.apkg, {n} carte)",
    ankiTsv: "Tabella modificabile (.tsv)",
    giftBtn: "Moodle (GIFT)",
    ankiHint: "Importa il .apkg in Anki (desktop/mobile) o il .gift in Moodle. Il .tsv serve a proporre correzioni.",
    loadError:
      "<b>Impossibile caricare le domande.</b> Esegui prima " +
      "<code>python run.py questions &amp;&amp; python run.py web</code>, poi servi la cartella.",
  },
  en: {
    pageTitle: "Lake Geneva boat licence — theory exam (practice)",
    h1: "Boat licence — theory exam",
    subtitle: "Category A (motorboat) · Lake Geneva",
    demoBanner:
      "<strong>Question bank in progress.</strong> All six themes are now covered, " +
      "but <em>signage</em> is still over-represented relative to the real exam. " +
      "The questions are derived from freely-reusable sources (Swiss federal law " +
      "ONI/RNL and openly-licensed references): this is not an official mock exam, " +
      "and the bank keeps growing.",
    fallbackBanner:
      "Questions shown in French — the {lang} translation is still being built.",
    unofficialBanner:
      "Unofficial study translation. Swiss law is not published in English; only the " +
      "FR/DE/IT versions are authoritative.",
    cfgQuestions: "Questions",
    cfgDuration: "Duration",
    cfgSuccess: "Pass mark",
    cfgScale: "Scoring",
    cfgAvailable: "Available",
    cfgPartial: "(of {target} targeted — bank still being built)",
    minUnit: "min",
    points: "points",
    ptsPerQuestion: "{n} pts/question",
    availableQuestions: "{n} questions",
    btnExam: "Mock exam (timed)",
    btnPractice: "Free practice",
    btnRestart: "Restart",
    btnValidate: "Check",
    btnNext: "Next",
    btnFinish: "Finish",
    btnSeeResult: "See result",
    sourceNote:
      "Source: federal ordinances (public domain). No question taken from a licensed bank.",
    progress: "Question {i} / {n}",
    multiHint: "One or two answers may be correct.",
    kbdHint: "Keys 1-3 to toggle · Enter to validate.",
    altSignal: "signal to identify",
    resultTitle: "Result",
    detailedCorrection: "Detailed correction",
    passed: "Passed",
    failed: "Failed",
    scoreLine: "{earned} / {total} points (threshold {pass})",
    faultPoints: "Fault points:",
    duration: "Duration:",
    partialExam:
      "Partial exam: {n} of {target} questions available. Indicative score.",
    yourChoice: "(your choice)",
    sourceLabel: "Source",
    stateOf: "(as of {date})",
    figureTag: "[figure]",
    footTagline: "Free study tool · built from primary legal sources",
    chooseDomains: "Study by topic:",
    chooseCanton: "Canton (exam duration):",
    choosePermit: "Category (exam):",
    studyOnly: "Study topic (practical exam) — not on the theory test.",
    permit_A: "Cat. A — motorboat",
    permit_D: "Cat. D — sailing",
    permitNote_A: "Motorboat with more than 6 kW of power " +
      "(4.4 kW on Lake Constance).",
    permitNote_D: "Sailboat with a sail area over 15 m² " +
      "(12 m² on Lake Constance). Theory exam identical to cat. A; " +
      "only the practical test differs.",
    poolLabel: "Question pool:",
    poolNational: "National bank",
    poolCore: "Common core",
    poolHint: "The common core keeps only the portable questions: universal " +
      "seamanship and the harmonised traffic code (CEVNI inland, COLREGS/IRPCS at " +
      "sea) — reusable across countries. The national bank adds each country's own law.",
    domainAll: "Select all",
    domainNone: "Deselect all",
    byDomain: "Score by topic",
    ankiTitle: "Study offline with Anki:",
    ankiApkg: "Anki deck (.apkg, {n} cards)",
    ankiTsv: "Editable table (.tsv)",
    giftBtn: "Moodle (GIFT)",
    ankiHint: "Import the .apkg into Anki (desktop/mobile) or the .gift into Moodle. The .tsv lets you suggest corrections.",
    loadError:
      "<b>Could not load the questions.</b> First run " +
      "<code>python run.py questions &amp;&amp; python run.py web</code>, then serve the folder.",
  },
};

/* Pick the active language: explicit ?lang=, then saved choice, then the
 * browser's preferred language, then French. Only the four supported codes. */
function detectLang() {
  const fromQuery = new URLSearchParams(location.search).get("lang");
  const saved = (() => { try { return localStorage.getItem("lang"); } catch { return null; } })();
  const nav = (navigator.languages || [navigator.language || ""]).map((l) => l.slice(0, 2));
  for (const cand of [fromQuery, saved, ...nav]) {
    if (cand && LANGS.includes(cand)) return cand;
  }
  return DEFAULT_LANG;
}

/* Translate `key` for `lang` with {placeholder} interpolation, falling back to
 * French for any string a translation happens to miss. */
function t(lang, key, vars) {
  let s = (STRINGS[lang] && STRINGS[lang][key]) ?? STRINGS[DEFAULT_LANG][key] ?? key;
  if (vars) for (const k in vars) s = s.replaceAll("{" + k + "}", vars[k]);
  return s;
}

function themeLabel(lang, theme) {
  return (THEME_LABELS[lang] && THEME_LABELS[lang][theme]) ||
    THEME_LABELS[DEFAULT_LANG][theme] || theme;
}

/* Strings for the practice-learning aids (recall-first, diagnostic feedback,
 * spaced repetition, confidence). Kept in their own table and merged into STRINGS
 * so the four language blocks above stay focused on the original exam chrome. Any
 * key a language misses still falls back to French via t(). */
const LEARN_STRINGS = {
  fr: {
    studySettings: "Options d'entraînement :",
    practiceOnly: "Ces options ne s'appliquent qu'à l'entraînement libre — l'examen blanc reste à l'identique.",
    optRecall: "Réponse d'abord",
    optRecallHint: "Cache les options : réfléchissez à la réponse avant de les voir (rappel actif).",
    optConfidence: "Niveau de confiance",
    optConfidenceHint: "Indiquez si vous êtes sûr ; les erreurs commises avec assurance reviennent en priorité.",
    optSpaced: "Révision espacée",
    optSpacedHint: "Présente d'abord les questions dues, jamais vues ou ratées, en alternant les thèmes.",
    recallPrompt: "Formulez votre réponse, puis affichez les options.",
    recallJot: "Notez votre réponse (facultatif)",
    recallReveal: "Afficher les options",
    confAsk: "Êtes-vous sûr ?",
    confSure: "Sûr",
    confUnsure: "Pas sûr",
    diagYouChose: "Votre réponse :",
    diagCorrect: "Bonne réponse :",
    hcError: "Erreur commise avec assurance — à revoir en priorité.",
    cfgDue: "À réviser",
    dueQuestions: "{n} questions dues",
    learnWhy: "Pourquoi ? — comprendre la règle",
  },
  de: {
    studySettings: "Übungsoptionen:",
    practiceOnly: "Diese Optionen gelten nur fürs freie Üben — die Prüfungssimulation bleibt unverändert.",
    optRecall: "Erst antworten",
    optRecallHint: "Verbirgt die Optionen: Überlegen Sie die Antwort, bevor Sie sie sehen (aktives Erinnern).",
    optConfidence: "Sicherheitsgrad",
    optConfidenceHint: "Geben Sie an, ob Sie sicher sind; selbstsicher falsche Antworten kommen zuerst zurück.",
    optSpaced: "Verteiltes Wiederholen",
    optSpacedHint: "Zeigt fällige, neue und falsch beantwortete Fragen zuerst, im Themenwechsel.",
    recallPrompt: "Formulieren Sie Ihre Antwort, dann zeigen Sie die Optionen.",
    recallJot: "Antwort notieren (optional)",
    recallReveal: "Optionen anzeigen",
    confAsk: "Sind Sie sicher?",
    confSure: "Sicher",
    confUnsure: "Unsicher",
    diagYouChose: "Ihre Antwort:",
    diagCorrect: "Richtige Antwort:",
    hcError: "Selbstsicher falsch beantwortet — vorrangig wiederholen.",
    cfgDue: "Fällig",
    dueQuestions: "{n} fällige Fragen",
    learnWhy: "Warum? — die Regel verstehen",
  },
  it: {
    studySettings: "Opzioni di allenamento:",
    practiceOnly: "Queste opzioni valgono solo per l'allenamento libero — l'esame simulato resta invariato.",
    optRecall: "Prima la risposta",
    optRecallHint: "Nasconde le opzioni: pensa alla risposta prima di vederle (richiamo attivo).",
    optConfidence: "Livello di sicurezza",
    optConfidenceHint: "Indica se sei sicuro; gli errori commessi con sicurezza tornano per primi.",
    optSpaced: "Ripasso dilazionato",
    optSpacedHint: "Mostra prima le domande dovute, mai viste o sbagliate, alternando i temi.",
    recallPrompt: "Formula la tua risposta, poi mostra le opzioni.",
    recallJot: "Annota la tua risposta (facoltativo)",
    recallReveal: "Mostra le opzioni",
    confAsk: "Sei sicuro?",
    confSure: "Sicuro",
    confUnsure: "Non sicuro",
    diagYouChose: "La tua risposta:",
    diagCorrect: "Risposta corretta:",
    hcError: "Errore commesso con sicurezza — da rivedere con priorità.",
    cfgDue: "Da ripassare",
    dueQuestions: "{n} domande dovute",
    learnWhy: "Perché? — capire la regola",
  },
  en: {
    studySettings: "Practice options:",
    practiceOnly: "These options apply to free practice only — the mock exam stays identical.",
    optRecall: "Recall first",
    optRecallHint: "Hides the options: think of the answer before you see them (active recall).",
    optConfidence: "Rate confidence",
    optConfidenceHint: "Say whether you're sure; confident-but-wrong answers come back first.",
    optSpaced: "Spaced review",
    optSpacedHint: "Shows due, never-seen and missed questions first, interleaving themes.",
    recallPrompt: "Form your answer, then show the options.",
    recallJot: "Jot your answer (optional)",
    recallReveal: "Show options",
    confAsk: "Are you sure?",
    confSure: "Sure",
    confUnsure: "Not sure",
    diagYouChose: "You chose:",
    diagCorrect: "Correct answer:",
    hcError: "High-confidence error — review this first.",
    cfgDue: "Due",
    dueQuestions: "{n} questions due",
    learnWhy: "Why? — understand the rule",
  },
};
for (const l in LEARN_STRINGS) STRINGS[l] = Object.assign(STRINGS[l] || {}, LEARN_STRINGS[l]);

/* Path-to-permit panel: the non-theory steps (age/medical/practical/application/
 * fees/validity) that turn a passed theory paper into an actual licence. The step
 * labels are keyed by the PathStep `code`; the bodies are authored per language in
 * the manifest (src/countries/<code>.py). Merged into STRINGS like LEARN_STRINGS. */
const PATH_STRINGS = {
  fr: {
    pathTitle: "Du théorique au permis : les étapes hors examen",
    pathIntro: "Réussir la théorie ne suffit pas. Voici le reste du parcours, d’après les sources officielles.",
    pathStep_age: "Âge minimum",
    pathStep_medical: "Vue & aptitude médicale",
    pathStep_first_aid: "Premiers secours",
    pathStep_practical: "Examen pratique",
    pathStep_application: "Demande & inscription",
    pathStep_fees: "Émoluments",
    pathStep_validity: "Validité & renouvellement",
    pathVerified: "vérifié le {date}",
    pathVolatile: "peut varier — à vérifier",
  },
  de: {
    pathTitle: "Von der Theorie zum Ausweis: die Schritte neben der Prüfung",
    pathIntro: "Die Theorie zu bestehen genügt nicht. Hier der restliche Weg, nach offiziellen Quellen.",
    pathStep_age: "Mindestalter",
    pathStep_medical: "Sehtest & ärztliche Eignung",
    pathStep_first_aid: "Nothilfe",
    pathStep_practical: "Praktische Prüfung",
    pathStep_application: "Gesuch & Anmeldung",
    pathStep_fees: "Gebühren",
    pathStep_validity: "Gültigkeit & Erneuerung",
    pathVerified: "geprüft am {date}",
    pathVolatile: "kann sich ändern — prüfen",
  },
  it: {
    pathTitle: "Dalla teoria alla licenza: i passi oltre l’esame",
    pathIntro: "Superare la teoria non basta. Ecco il resto del percorso, secondo le fonti ufficiali.",
    pathStep_age: "Età minima",
    pathStep_medical: "Vista e idoneità medica",
    pathStep_first_aid: "Primo soccorso",
    pathStep_practical: "Esame pratico",
    pathStep_application: "Domanda e iscrizione",
    pathStep_fees: "Emolumenti",
    pathStep_validity: "Validità e rinnovo",
    pathVerified: "verificato il {date}",
    pathVolatile: "può variare — da verificare",
  },
  en: {
    pathTitle: "From theory to licence: the steps beyond the exam",
    pathIntro: "Passing the theory isn’t enough. Here’s the rest of the path, from official sources.",
    pathStep_age: "Minimum age",
    pathStep_medical: "Eyesight & medical fitness",
    pathStep_first_aid: "First aid",
    pathStep_practical: "Practical exam",
    pathStep_application: "Application & registration",
    pathStep_fees: "Fees",
    pathStep_validity: "Validity & renewal",
    pathVerified: "verified {date}",
    pathVolatile: "may change — verify",
  },
};
for (const l in PATH_STRINGS) STRINGS[l] = Object.assign(STRINGS[l] || {}, PATH_STRINGS[l]);

/* Catalogue-coverage banner. The honest framing the project trades for: a
 * derived bank (CH/FR) shows its measured coverage of the harmonised core plus
 * the "do a final official-bank mock" caveat — never an implied "ready to pass";
 * the official German bank says so plainly. Fed from MANIFEST.coverage, which the
 * bundler reads from the committed data/coverage.lock.json (src/validate.py). */
const COVERAGE_STRINGS = {
  fr: {
    coverageOfficial: "✓ Ce sont les questions du <b>catalogue officiel ELWIS</b> — l’examen puise dans cette même banque.",
    coverageDerived: "Banque <b>dérivée du droit</b>, pas du catalogue d’examen officiel. Couverture mesurée du tronc harmonisé&nbsp;: {tracks}. Elle couvre le fondement juridique et le raisonnement — avant l’examen, faites un <b>examen blanc depuis une source officielle</b>.",
    coverageTrack: "{base} {pct}&nbsp;% (de la part mesurable, {slice}&nbsp;%)",
    coverageBase_cevni: "code fluvial", coverageBase_colregs: "code maritime",
    coverageBase_universal: "matelotage",
  },
  de: {
    coverageOfficial: "✓ Dies sind die Fragen des <b>amtlichen ELWIS-Katalogs</b> — die Prüfung schöpft aus derselben Bank.",
    coverageDerived: "<b>Aus dem Recht abgeleitete</b> Bank, nicht der amtliche Prüfungskatalog. Gemessene Abdeckung des harmonisierten Kerns: {tracks}. Sie deckt die rechtliche Grundlage und das Verständnis ab — mache vor der Prüfung einen <b>Probetest aus amtlicher Quelle</b>.",
    coverageTrack: "{base} {pct}&nbsp;% (vom messbaren Teil, {slice}&nbsp;%)",
    coverageBase_cevni: "Binnen", coverageBase_colregs: "See",
    coverageBase_universal: "Seemannschaft",
  },
  it: {
    coverageOfficial: "✓ Queste sono le domande del <b>catalogo ufficiale ELWIS</b> — l’esame attinge alla stessa banca.",
    coverageDerived: "Banca <b>derivata dalla legge</b>, non dal catalogo d’esame ufficiale. Copertura misurata del nucleo armonizzato: {tracks}. Copre le basi giuridiche e il ragionamento — prima dell’esame, fai una <b>simulazione da fonte ufficiale</b>.",
    coverageTrack: "{base} {pct}&nbsp;% (della parte misurabile, {slice}&nbsp;%)",
    coverageBase_cevni: "codice fluviale", coverageBase_colregs: "codice marittimo",
    coverageBase_universal: "marineria",
  },
  en: {
    coverageOfficial: "✓ These are the <b>official ELWIS catalogue</b> questions — the exam draws from this same bank.",
    coverageDerived: "Bank <b>derived from the law</b>, not the official exam catalogue. Measured coverage of the harmonised core: {tracks}. It covers the legal foundation and the reasoning — before your exam, do a <b>final mock from an official-bank source</b>.",
    coverageTrack: "{base} {pct}% (of the {slice}% measurable)",
    coverageBase_cevni: "inland code", coverageBase_colregs: "sea code",
    coverageBase_universal: "seamanship",
  },
};
for (const l in COVERAGE_STRINGS) STRINGS[l] = Object.assign(STRINGS[l] || {}, COVERAGE_STRINGS[l]);
