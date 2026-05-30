# Boat-permit — Bootsführerschein-Regeln aus geprüften Quellen lernen

**Sprachen:** [English](README.md) · [Français](README.fr.md) · **Deutsch** · [Italiano](README.it.md)

Ein offenes Framework zum Lernen für **nationale Theorieprüfungen des
Bootsführerscheins**, das **ausschließlich** auf gemeinfreiem Recht und eindeutig
weiterverwendbaren Quellen aufbaut. Es deckt heute drei Länder ab —
**🇫🇷 Frankreich · 🇩🇪 Deutschland · 🇨🇭 Schweiz** — hinter einer Pipeline und einem
Player, und es ist so konzipiert, dass das Hinzufügen eines Landes eine einzige neue
Datei erfordert, kein Fork.

Für jedes Land liefert es drei Dinge:

1. eine strukturierte, versionierte **Wissensbasis** (KB), die aus dem Recht des
   jeweiligen Landes abgeleitet ist,
2. eine **quellenbelegte Übungs-Fragenbank** und
3. einen abhängigkeitsfreien **statischen Player** (Browser / GitHub Pages) mit
   **Anki**- und **Moodle GIFT**-Exporten.

## Die rechtliche Grenze (der ganze Sinn)

Jede amtliche Prüfung beruht auf einer Fragenbank, und die kostenpflichtigen
Vorbereitungs-Apps verpacken diese neu. Dieses Projekt **rührt das bewusst nicht an**.
Die harte Regel, die in jedem Land identisch angewendet wird:

- **Es übernimmt** nur Recht und Quellen, die gemeinfrei sind oder eine ausdrückliche
  Wiederverwendungslizenz tragen. Herkunft + ein Lizenzhinweis werden bei **jeder**
  Einheit und **jeder** Frage gespeichert.
- **Es scrapt, speichert oder reproduziert niemals** eine proprietäre Fragenbank oder
  die Fragen/Erklärungen einer kostenpflichtigen App.
- **Jede Übungsfrage ist aus Primärquellen abgeleitet** und trägt einen Quellenverweis
  zurück auf den Artikel, die Regel oder die Abbildung, aus der sie stammt. Eine Frage
  aus dem Gedächtnis zu formulieren ist verboten — die Quelle ist die Autorität.

Wie sich diese Regel pro Land konkret auswirkt:

| Land | Rechtsgrundlage (öffentlich/weiterverwendbar) | Fragengrundlage |
|---------|-----------------------------|----------------|
| 🇫🇷 **Frankreich** | Légifrance / DILA LEGI unter **Licence Ouverte / Etalab** (französische amtliche Erlasse tragen kein Urheberrecht) | Aus dem übernommenen Recht abgeleitet — die proprietären QCM-Banken der Betreiber (La Poste/Dekra/SGS/Bureau Veritas) werden **nie** angerührt |
| 🇩🇪 **Deutschland** | gesetze-im-internet.de XML, gemeinfrei nach **§5(1) UrhG** | Die amtlichen **ELWIS** *amtlichen Fragenkataloge* sind nach **§5(2) UrhG** wortgetreu weiterverwendbar (Quelle www.elwis.de angeben, keine Änderung) — unverändert übernommen |
| 🇨🇭 **Schweiz** | Fedlex Akoma Ntoso XML, schweizerisches Bundesrecht ist gemeinfrei | Aus dem Recht abgeleitet — die asa-lizenzierte Bank, die von den kostenpflichtigen Apps neu verpackt wird, wird **nie** angerührt |

## Schnellstart

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

KB-Builds werden zwischengespeichert und sind erneut ausführbar; `--force` lädt neu.
Die Fragen- und Web-Schritte sind reine Transformationen über den vorherigen Ausgaben.

## Funktionsweise

Die Pipeline ist für jedes Land gleich; nur der länderspezifische Deskriptor ändert
sich.

### Phase 1 — Wissensbasis

Drei unabhängig voneinander erneut ausführbare Stufen, von denen jede die Ausgabe der
vorherigen liest:

| Stufe | Befehl | Was sie tut |
|-------|---------|--------------|
| **Fetch** | `run.py fetch [--country X]` | Lädt Rohquellen wortgetreu nach `data/raw/<id>/`, mit einem `manifest.json`, das URL + Abrufdatum + Rechtsfassung festhält. Lädt nur bei `--force` erneut. |
| **Parse** | `run.py parse [--country X]` | Wandelt jede Rohquelle in strukturierte `KnowledgeUnit`s um (rein, ohne Netzwerk). Ein Parser pro Quellentyp — Akoma Ntoso (CH), gii XML (DE), LEGI XML (FR), COLREG PDF (INT), MediaWiki/HTML. |
| **Normalize** | (Teil von `build`) | Führt zu einer SQLite-KB zusammen, lokalisiert Bild-Assets, verknüpft Artikel ↔ Abbildungen, taggt jede Einheit zum Prüfungsthema des jeweiligen Landes, prägt eine Version ein. |

Mit `--only` auf bestimmte Quellen beschränken. Das Recht jedes Landes (Zeichen,
Betonnung, Lichter, Schallsignale) führt die Diagramme als lokalisierte Bild-Assets
mit sich, beschriftet aus den Anhangstabellen und mit den zitierenden Artikeln
verknüpft.

### Phase 2 — Fragenbank

| Schritt | Befehl | Was er tut |
|------|---------|--------------|
| **Figures** | `run.py questions` | Erzeugt deterministisch Bilderkennungsfragen aus beschrifteten Anhangsdiagrammen. Verwechslungs-Distraktoren nach Signaltyp gewählt; sha1-seeded, damit die Ausgabe stabil ist. Automatisch freigegeben. |
| **Derive / draft** | `run.py draft …` · `run.py fr` | Entwirft Fragen streng **aus übernommenem Quelltext** (ein lexikalischer Grounding-Wächter verwirft wahrscheinliche Halluzinationen), jede an einen maßgeblichen Quellenverweis geheftet. Landet als **`pending`**. |
| **Catalogue ingest** | `run.py questions --country DE` | Übernimmt einen amtlichen weiterverwendbaren Katalog (Deutschlands ELWIS) **wortgetreu**, jede Frage getaggt + mit ihrer §5-Attribuierung. |
| **Review** | `run.py review --list / --approve / --reject` | Menschliches Prüf-Gate. Nur `auto_approved`- + `approved`-Fragen werden jemals exportiert. |
| **Web** | `run.py web` | Exportiert jede freigegebene Bank erneut nach `questions.<lang>.json`, bündelt die Abbildungs-Assets in `web/` und schreibt die sprachspezifischen **Anki-Decks** (`web/anki/`) + **Moodle GIFT**-Dateien (`web/gift/`). |

## Die Länder

Alle drei sind gleichwertig: Jedes ist ein Deskriptor in `src/countries/`, der seine
Rechtsquellen, die Prüfungsthemen-Taxonomie + den Tagger, den Führerschein-Katalog, die
Prüfungsregeln und die regionalen Regelungen deklariert — die Konfiguration, die die
Pipeline verarbeitet. Das Hinzufügen eines Landes ist eine neue Datei + eine
Registry-Zeile (`src/countries/registry.py`), sodass parallele Arbeit nicht kollidiert.

### 🇫🇷 Frankreich — permis plaisance

Der **permis plaisance** in zwei Optionen: **côtière** (maritim, ≤6 NM von einem
Schutzort, Tag und Nacht) und **eaux intérieures** (Flüsse, Kanäle, Seen). Die Prüfung
ist national — **40 Single-Answer-QCM, bestanden bei ≤5 Fehlern (35/40), ~30 Min.**,
überall identisch (keine regionale Varianz). Frankreich ist **seed- + law-derived**:
Fragen werden **aus** dem übernommenen französischen Recht formuliert, niemals aus den
proprietären Betreiberbanken.

- **Recht (Licence Ouverte / Etalab):** Das Projekt übernimmt die umfangreichen
  **DILA LEGI**-Open-Data — das französische Pendant zu Fedlex — für den **Code des
  transports, Teil 4** (das RGP, Frankreichs CEVNI-Umsetzung), den **Code de
  l'environnement** (MARPOL/Einleitungen), das **décret & arrêté du 28 sept. 2007**
  (das référentiel) und die **Division 245** (≈1.346 in Kraft befindliche Artikel).
  Maritimes Grounding, das LEGI nicht trägt — **RIPAM/COLREG, IALA-Region-A-Betonnung,
  SHOM**-Gezeiten/Bezugsniveaus — wird als geprüfter Referenzfakten-Korpus übernommen
  (Fakten sind nicht urheberrechtlich schützbar; jeder auf seine Primärquelle
  belegt).
- **Build:** `python run.py fr` → beide Options-Banken + die `web/fr/`-Player.

### 🇩🇪 Deutschland — Sportbootführerschein

Deutschlands **Sportbootführerschein**, mit dem umfangreichsten Katalog der drei.

- **Recht (§5(1) UrhG, gemeinfrei):** gesetze-im-internet.de stellt jede Verordnung als
  strukturiertes XML unter `<slug>/xml.zip` bereit. `run.py build --country DE` lädt
  **SeeSchStrO, BinSchStrO, die KVR/COLREG, die SpFV und die RheinSchPV** (≈1.750
  Artikeleinheiten inkl. Betonnungs-/Licht-/Zeichendiagrammen), getaggt zu einer
  deutschen Taxonomie (Verkehrsregeln, Schifffahrtszeichen, Lichter/Signale,
  Wetterkunde, …).
- **Amtlicher Katalog (§5(2) UrhG, weiterverwendbar):** Anders als die nicht
  zugängliche Schweizer Bank sind die **ELWIS** *amtlichen Fragenkataloge* für SBF
  See/Binnen weiterverwendbar *"solange der Inhalt unverändert bleibt und als Quelle
  www.elwis.de angegeben wird"*. `run.py questions --country DE` übernimmt beide
  Kataloge **wortgetreu** (≈515 Fragen nach Deduplizierung der gemeinsamen
  Basisfragen), jede zu einem Thema + Prüfungsblock getaggt, mit der §5-Attribuierung
  in ihrer Herkunft. Da die Wiederverwendung an *keine Änderung* gebunden ist, ist die
  deutsche Bank nur deutschsprachig und Optionen werden zur Anzeige nur **umsortiert**,
  niemals umformuliert.
- **Führerscheine & Prüfung:** der bundesweite **SBF See / SBF Binnen** (Motor / Segel
  / beides), der freiwillige **SKS / SSS / SHS** und das trinationale
  **Bodensee-Schifferpatent**. Die Bewertung ist **blockbasiert** (z. B. ≥5/7 Basis
  **und** ≥18/23 spezifisch), in `questions/schema.py:grade_exam_blocks`. Die Betonnung
  ist **IALA Region A**. Eine Reform 2025–26 ist als *pending* gekennzeichnet, nicht als
  geltendes Recht (`countries/de.py:REFORM_NOTE`).
- **Player:** Die **🇩🇪 Deutschland** der Länderleiste öffnet `web/de/`, wo ein
  Führerschein-Auswähler die echte **blockstrukturierte Prüfung** steuert.

### 🇨🇭 Schweiz — cat-A-Motorboot (+ cat-D-Gerüst)

Die Theorieprüfung für die **Kategorie-A-Motorboote**, interkantonal standardisiert
durch die **VKS** (Genfs OCV verwaltet den nationalen Standard auf dem Lac Léman).

- **Recht (gemeinfrei):** Fedlex-Seiten werden per JS gerendert, daher wird das
  Seiten-HTML nie gescrapt — der Build löst das **Akoma Ntoso XML** (Artikeltext) und
  seine Anhangsbilder über den Fedlex-**SPARQL-Endpunkt** + Filestore auf. Quellen: die
  **ONI** (RS 747.201.1) und die **RNL** (Léman, RS 747.221.1), zuzüglich frei
  lizenzierter Météo- und Matelotage-Quellen.
- **Prüfung:** **60 Fragen · 50 Minuten · 180 Punkte · bestanden bei 165/180.** Jede
  Frage hat 3 Antworten, von denen **1–2 richtig** sind (Multi-Select), bewertet nach
  dem **Alles-oder-nichts**-Prinzip. Die einzige kantonsspezifische Varianz ist das
  **Zeitlimit** (50 Min. GE/VD · 45 Min. Bern), modelliert in `src/cantons.py` und im
  Player als **Kantonsauswähler** dargestellt.
- **Führerscheine:** **cat-A** ist das vollständig fundierte Sechs-Themen-Ziel
  (Définitions, Météorologie, Lois, Signalisation, Matelotage, Eaux frontalières).
  **cat-D** (voile) ist als Gerüst angelegt — sie teilt den cat-A-Kern und ergänzt ein
  `voile`-Thema, in Erwartung einer frei lizenzierten Quelle zur Segeltechnik.
- **Build:** `python run.py build` + `python run.py questions` → `web/` (der Standard,
  sodass ein nackter Build der Schweizer Build ist).

## Harmonisierte Codes — die supranationale Ebene (`INT`)

Über den nationalen Prüfungen stehen die **harmonisierten Navigationscodes**, die die
Bank jedes Landes teilt: **COLREGS** (maritime Kollisionsregeln) und **CEVNI** (der
europäische Code der Binnenwasserstraßen) — die Wurzeln des Regelungsbaums in
`src/jurisdictions.py`. Das `INT`-Registry-Mitglied (`src/countries/intl.py`) fundiert
sie in ihrem **kanonischen Text**, statt nur indirekt über nationale Umsetzungen. Es ist
reine Quelle — keine Führerscheine, kein Player-Bundle — und erscheint daher nie im
Länderauswähler.

- **COLREG — übernommen.** Die wortgetreuen International Regulations (1972) sind ein
  **US-Government-Werk** (gemeinfrei, 17 USC §105) in der Veröffentlichung der US Coast
  Guard. `run.py build --country INT` lädt das USCG-„Navigation Rules“-PDF, und der
  Parser (`src/parsers/colreg.py`) behält nur dessen *International*-Seiten und
  segmentiert die 38 Rules + Annexes I–IV. Die urheberrechtlich geschützte konsolidierte
  Ausgabe der IMO wird **nicht** verwendet.
- **CEVNI — nicht übernommen (Lizenzhürde).** Der kanonische UNECE-Text (Resolution
  No. 24, Rev.6) ist all-rights-reserved: Die UN-Politik verlangt schriftliche
  Genehmigung und untersagt Weiterverbreitung/Bearbeitungen, sodass er die
  Wiederverwendungsregel des Projekts nicht erfüllt. Er wird als `Reference` erfasst;
  ein Antrag auf Reproduktionsgenehmigung wurde an die UNECE gesandt und steht aus. Bis
  zur Erteilung bleibt die CEVNI-Basis über die bereits übernommenen gemeinfreien
  nationalen Binnenumsetzungen fundiert.

### Gemeinsamer Kern vs. nationale Bank

Da so viele Inhalte harmonisiert sind, wird jede Frage zur Build-Zeit (`src/scope.py`)
als eine von `universal` (Seemannschaft/Wetter/Erste Hilfe) · `cevni` (Binnen-Code) ·
`colregs` (Maritim-Code) · `national` (Gesetz) · `local` (ein Gewässer) klassifiziert.
Die portierbaren Basen werden über die Banken **aller** Länder pro Sprache zu additiven
`web/questions.<base>.<lang>.json`-Bundles zusammengeführt, und der **National ⟷
Common-core**-Umschalter des Players setzt `universal + (cevni | colregs)` für den Track
des aktiven Führerscheins zusammen. Nationale Bundles bleiben über Builds hinweg
**byte-identisch** — eine nachverfolgte Invariante. Siehe `docs/scope.md`.

## Der Player

`web/` ist abhängigkeitsfreies Vanilla-JS. Er lädt die Bank der aktiven Sprache, liest
die Prüfungskonfiguration aus ihren `meta` und führt eine chronometrierte **Prüfung**
sowie einen **Übungs**-Modus mit quellenbelegten Korrekturen aus. Sie können **nach
Themengebiet lernen** (umschalten, aus welchen Themen ein Durchlauf zieht), den
**National ⟷ Common-core**-Pool umschalten, und der Ergebnisbildschirm schlüsselt die
**Punktzahl pro Themengebiet** auf. Die **🇫🇷 / 🇩🇪 / 🇨🇭 Länderleiste** wechselt
zwischen den nationalen Playern, die jeweils dieselbe Engine mit ihren eigenen
Prüfungsregeln wiederverwenden. Der Player bietet außerdem das **Anki-Deck** und die
**Moodle GIFT**-Datei für die aktive Sprache als Ein-Klick-Downloads.

### Sprachen

Die Player-Oberfläche ist in **Französisch, Deutsch, Italienisch und Englisch**
übersetzt, und Frageninhalte werden pro Sprache erstellt. Wo das amtliche Recht eines
Landes nicht in einer Sprache veröffentlicht ist (z. B. Englisch nirgends, Italienisch
nur in der CH), wird die Bank als **unofficial** gekennzeichnet oder weicht mit einem
sichtbaren Hinweis auf die maßgebliche Sprache aus. UI-Strings liegen in
`web/i18n.js`; `run.py web` gibt eine `questions.<lang>.json` pro Sprache plus ein
`languages.json`-Manifest aus.

### Anki- & Moodle-Exporte

| Werkzeug | Befehl | Was es tut |
|------|---------|--------------|
| **Anki** | `python tools/anki.py export [lang]` | Eine echte `.apkg` (Zip + SQLite, Abbildungen gebündelt, ein **Subdeck pro Thema**) und eine editierbare `.tsv`. `import file.tsv --apply` führt Änderungen als **pending**-Entwürfe zurück. Nur Stdlib. |
| **GIFT** | `python tools/gift.py export [lang]` | Eine **Moodle GIFT**-Datei, ein `$CATEGORY` pro Thema, Abbildungen als base64-`data:`-URIs eingebettet, sodass sie eigenständig ist. Nur Stdlib. |

Das Anki-Mapping ist **verlustfrei für editierbaren Text**, aber **strukturgesperrt**:
welche Optionen richtig sind, das Bild und die Herkunft verbleiben im Eigentum der
Bank, sodass eine aus Anki/TSV reimportierte Änderung nie unbemerkt eine Antwort
umdrehen kann — sie landet als `pending`-Entwurf zur erneuten Prüfung. Alle Paket-IDs
sind inhaltsabgeleitet (sha1) und mtimes fixiert, sodass ein Rebuild byte-identisch ist.

## Aufbau

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

Alles offline; kein Netzwerk und kein API-Key nötig.

## Lizenz

Das Werkzeug in diesem Repository steht zur Wiederverwendung offen. Übernommene Inhalte
behalten ihre eigene Lizenz, pro Einheit und pro Frage erfasst: Schweizerisches/
französisches Bundesrecht und das COLREG (USCG) sind gemeinfrei; französische Open Data
stehen unter Licence Ouverte / Etalab; deutsches Recht ist §5(1) UrhG und der
ELWIS-Katalog §5(2) UrhG (Quelle www.elwis.de angeben, unverändert);
Wikipedia-Matelotage-Material ist CC BY-SA 4.0; Météo-/kantonale Seiten sind amtliche
Quellen, die mit Quellenangabe verwendet werden.
