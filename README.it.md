# Boat-permit — impara le regole della navigazione da fonti verificate

**Lingue:** [English](README.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · **Italiano**

Un framework aperto per lo studio degli **esami teorici per la patente nautica
nazionale**, costruito **esclusivamente** a partire da norme di pubblico dominio e
da riferimenti chiaramente riutilizzabili. Oggi copre tre Paesi —
**🇫🇷 Francia · 🇩🇪 Germania · 🇨🇭 Svizzera** — dietro un'unica pipeline e un unico
player, ed è progettato in modo che aggiungere un Paese richieda un solo file nuovo,
non un fork.

Per ciascun Paese fornisce tre cose:

1. una **base di conoscenza** (KB) strutturata e versionata, derivata dalla legge di
   quel Paese,
2. una **banca di domande di pratica con citazione delle fonti**, e
3. un **player statico** senza dipendenze (browser / GitHub Pages) con esportazioni
   verso **Anki** e **Moodle GIFT**.

## Il confine legale (il vero punto)

Ogni esame ufficiale è sostenuto da una banca di domande, e le app a pagamento per la
preparazione la riconfezionano. Questo progetto deliberatamente **non tocca nulla di
tutto ciò**. La regola ferrea, applicata in modo identico in ogni Paese:

- **Acquisisce** soltanto norme e riferimenti che siano di pubblico dominio o che
  rechino una licenza esplicita di riutilizzo. La provenienza + una nota sulla licenza
  sono memorizzate su **ogni** unità e su **ogni** domanda.
- **Non esegue mai scraping, non memorizza né riproduce** una banca di domande
  proprietaria né le domande/spiegazioni di alcuna app a pagamento.
- **Ogni domanda di pratica è derivata da fonti primarie** e reca una citazione
  all'articolo, alla regola o alla figura da cui proviene. È vietato comporre una
  domanda a memoria — la fonte è l'autorità.

Come si concretizza questa regola in ciascun Paese:

| Paese | Base normativa (pubblica/riutilizzabile) | Base delle domande |
|---------|-----------------------------|----------------|
| 🇫🇷 **Francia** | Légifrance / DILA LEGI sotto **Licence Ouverte / Etalab** (gli atti ufficiali francesi non recano copyright) | Derivate dalla legge acquisita — le banche QCM proprietarie degli operatori (La Poste/Dekra/SGS/Bureau Veritas) **non** vengono **mai** toccate |
| 🇩🇪 **Germania** | XML di gesetze-im-internet.de, di pubblico dominio ai sensi del **§5(1) UrhG** | Gli *amtliche Fragenkataloge* ufficiali di **ELWIS** sono riutilizzabili alla lettera ai sensi del **§5(2) UrhG** (citando www.elwis.de, senza modifiche) — acquisiti così come sono |
| 🇨🇭 **Svizzera** | XML Akoma Ntoso di Fedlex, il diritto federale svizzero è di pubblico dominio | Derivate dalla legge — la banca su licenza asa riconfezionata dalle app a pagamento **non** viene **mai** toccata |

## Avvio rapido

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

Le build della KB sono memorizzate in cache e rieseguibili; `--force` riesegue il
recupero. Gli step delle domande e del web sono trasformazioni pure sugli output
precedenti.

## Come funziona

La pipeline è la stessa per ogni Paese; cambia soltanto il descrittore specifico del
Paese.

### Fase 1 — base di conoscenza

Tre stadi rieseguibili in modo indipendente, ciascuno dei quali legge l'output del
precedente:

| Stadio | Comando | Cosa fa |
|-------|---------|--------------|
| **Fetch** | `run.py fetch [--country X]` | Recupera le fonti grezze in `data/raw/<id>/`, alla lettera, con un `manifest.json` che registra URL + data di recupero + versione legale. Non riesegue il recupero salvo `--force`. |
| **Parse** | `run.py parse [--country X]` | Trasforma ciascuna fonte grezza in `KnowledgeUnit` strutturate (puro, nessuna rete). Un parser per tipo di fonte — Akoma Ntoso (CH), gii XML (DE), LEGI XML (FR), COLREG PDF (INT), MediaWiki/HTML. |
| **Normalize** | (parte di `build`) | Unisce in un'unica KB SQLite, localizza gli asset immagine, collega articoli ↔ figure, assegna a ogni unità il tema d'esame di quel Paese, appone una versione. |

Limita a fonti specifiche con `--only`. La legge di ciascun Paese (segnaletica,
sistema di boe, fanali, segnali sonori) reca i diagrammi come asset immagine
localizzati, con didascalie tratte dalle tabelle degli allegati e collegati agli
articoli citanti.

### Fase 2 — banca di domande

| Step | Comando | Cosa fa |
|------|---------|--------------|
| **Figure** | `run.py questions` | Genera deterministicamente domande di riconoscimento delle figure dai diagrammi degli allegati provvisti di didascalia. Distrattori da set di confusione indicizzati per tipo di segnale; con seed sha1, così l'output è stabile. Approvate automaticamente. |
| **Derive / draft** | `run.py draft …` · `run.py fr` | Redige domande rigorosamente **dal testo della fonte acquisita** (un controllo di ancoraggio lessicale scarta le probabili allucinazioni), ciascuna ancorata a una citazione autorevole. Atterra come **`pending`**. |
| **Acquisizione catalogo** | `run.py questions --country DE` | Acquisisce un catalogo ufficiale riutilizzabile (l'ELWIS tedesco) **alla lettera**, ogni domanda taggata + recante la sua attribuzione §5. |
| **Review** | `run.py review --list / --approve / --reject` | Gate di revisione umana. Solo le domande `auto_approved` + `approved` vengono mai esportate. |
| **Web** | `run.py web` | Riesporta ogni banca approvata in `questions.<lang>.json`, raggruppa gli asset delle figure in `web/`, e scrive i **mazzi Anki** per lingua (`web/anki/`) + i file **Moodle GIFT** (`web/gift/`). |

## I Paesi

Tutti e tre sono di prima classe: ciascuno è un descrittore in `src/countries/` che
dichiara le proprie fonti normative, la tassonomia dei temi d'esame + il tagger, il
catalogo delle patenti, le regole d'esame e i regimi regionali — la configurazione che
la pipeline consuma. Aggiungere un Paese richiede un solo file nuovo + una sola riga
nel registro (`src/countries/registry.py`), così il lavoro in parallelo non collide.

### 🇫🇷 Francia — permis plaisance

Il **permis plaisance** in due opzioni: **côtière** (marittima, ≤6 NM da un riparo,
giorno e notte) ed **eaux intérieures** (fiumi, canali, laghi). L'esame è nazionale —
**40 QCM a risposta singola, superato con ≤5 errori (35/40), ~30 min**, identico
ovunque (nessuna variazione regionale). La Francia è **seed- + law-derived**: le
domande sono composte **a partire** dalla legge francese acquisita, mai dalle banche
proprietarie degli operatori.

- **Legge (Licence Ouverte / Etalab):** il progetto acquisisce in blocco gli open data
  **DILA LEGI** — l'analogo francese di Fedlex — per il **Code des transports, Part 4**
  (l'RGP, l'implementazione francese di CEVNI), il **Code de l'environnement**
  (MARPOL/rejets), il **décret & arrêté du 28 sept. 2007** (il référentiel), e la
  **Division 245** (≈1.346 articoli in vigore). L'ancoraggio marittimo che LEGI non
  copre — **RIPAM/COLREG, sistema di boe IALA Region A, SHOM** maree/datum — viene
  acquisito come corpus verificato di fatti di riferimento (i fatti non sono soggetti a
  copyright; ciascuno citato alla sua fonte primaria).
- **Build:** `python run.py fr` → entrambe le banche d'opzione + i player `web/fr/`.

### 🇩🇪 Germania — Sportbootführerschein

Lo **Sportbootführerschein** tedesco, con il catalogo più ricco dei tre.

- **Legge (§5(1) UrhG, pubblico dominio):** gesetze-im-internet.de serve ciascuna
  ordinanza come XML strutturato su `<slug>/xml.zip`. `run.py build --country DE`
  recupera **SeeSchStrO, BinSchStrO, la KVR/COLREG, la SpFV e la RheinSchPV** (≈1.750
  unità-articolo incl. diagrammi di boe/fanali/segnali), taggate a una tassonomia
  tedesca (Verkehrsregeln, Schifffahrtszeichen, Lichter/Signale, Wetterkunde, …).
- **Catalogo ufficiale (§5(2) UrhG, riutilizzabile):** a differenza della banca svizzera
  off-limits, gli *amtliche Fragenkataloge* di **ELWIS** per SBF See/Binnen sono
  riutilizzabili *"solange der Inhalt unverändert bleibt und als Quelle www.elwis.de
  angegeben wird"*. `run.py questions --country DE` acquisisce entrambi i cataloghi
  **alla lettera** (≈515 domande dopo la deduplicazione delle Basisfragen condivise),
  ciascuna taggata a un tema + blocco d'esame con l'attribuzione §5 nella sua
  provenienza. Poiché il riutilizzo è subordinato all'*assenza di modifiche*, la banca
  tedesca è solo in tedesco e le opzioni vengono unicamente **riordinate** per la
  visualizzazione, mai riformulate.
- **Patenti ed esame:** le federali **SBF See / SBF Binnen** (motore / vela / entrambi),
  le volontarie **SKS / SSS / SHS**, e il trinazionale **Bodensee-Schifferpatent**. La
  valutazione è **a blocchi** (es. ≥5/7 Basis **e** ≥18/23 spezifisch), in
  `questions/schema.py:grade_exam_blocks`. Il sistema di boe è **IALA Region A**. Una
  riforma 2025–26 è segnalata come *pending*, non diritto consolidato
  (`countries/de.py:REFORM_NOTE`).
- **Player:** la **🇩🇪 Deutschland** della countrybar apre `web/de/`, dove un selettore
  di patente guida il vero **esame strutturato a blocchi**.

### 🇨🇭 Svizzera — motoscafo cat-A (+ impalcatura cat-D)

L'esame teorico per il **motoscafo categoria A**, standardizzato a livello
intercantonale dalla **VKS** (l'OCV di Ginevra amministra lo standard nazionale sul
Lac Léman).

- **Legge (pubblico dominio):** le pagine Fedlex sono renderizzate in JS, quindi l'HTML
  della pagina non viene mai sottoposto a scraping — la build risolve l'**XML Akoma
  Ntoso** (testo degli articoli) e le immagini dei suoi allegati tramite l'**endpoint
  SPARQL** di Fedlex + filestore. Fonti: l'**ONI** (RS 747.201.1) e l'**RNL** (Léman,
  RS 747.221.1), più riferimenti météo e di matelotage con licenza libera.
- **Esame:** **60 domande · 50 minuti · 180 punti · superato a 165/180.** Ogni domanda
  ha 3 risposte di cui **1–2 corrette** (selezione multipla), valutate **tutto o
  niente**. L'unica variazione per cantone è il **limite di tempo** (50 min GE/VD · 45
  min Berna), modellato in `src/cantons.py` e reso disponibile come **selettore di
  cantone** nel player.
- **Patenti:** la **cat-A** è il target pienamente ancorato a sei temi (Définitions,
  Météorologie, Lois, Signalisation, Matelotage, Eaux frontalières). La **cat-D**
  (voile) è impalcata — condivide il nucleo della cat-A e aggiunge un tema `voile`, in
  attesa di una fonte sulla tecnica velica con licenza libera.
- **Build:** `python run.py build` + `python run.py questions` → `web/` (l'impostazione
  predefinita, quindi una build nuda è la build svizzera).

## Codici armonizzati — il livello sovranazionale (`INT`)

Al di sopra degli esami nazionali si collocano i **codici di navigazione armonizzati**
condivisi dalla banca di ogni Paese: **COLREGS** (regole marittime anticollisione) e
**CEVNI** (il codice europeo delle vie navigabili interne) — le radici dell'albero dei
regimi in `src/jurisdictions.py`. Il membro `INT` del registro
(`src/countries/intl.py`) li ancora al loro **testo canonico** anziché solo
indirettamente tramite le trasposizioni nazionali. È solo sourcing — nessuna patente,
nessun bundle del player — quindi non compare mai nel selettore di Paese.

- **COLREG — acquisito.** Le International Regulations (1972) alla lettera sono un'**opera
  del Governo degli Stati Uniti** (pubblico dominio, 17 USC §105) come pubblicate dalla
  US Coast Guard. `run.py build --country INT` recupera il PDF "Navigation Rules" della
  USCG e il parser (`src/parsers/colreg.py`) conserva solo le sue pagine
  *International*, segmentando le 38 Rules + gli Annexes I–IV. L'edizione consolidata
  protetta da copyright dell'IMO **non** viene usata.
- **CEVNI — non acquisito (barriera di licenza).** Il testo canonico UNECE (Risoluzione
  n. 24, Rev.6) è all-rights-reserved: la policy ONU richiede un permesso scritto e
  vieta la ridistribuzione/i derivati, quindi non supera la regola di riutilizzo del
  progetto. È registrato come `Reference`; una richiesta di permesso di riproduzione è
  stata inviata all'UNECE ed è in attesa. Finché non sarà concessa, la base CEVNI resta
  ancorata tramite le trasposizioni nazionali per le acque interne di pubblico dominio
  già acquisite.

### Nucleo condiviso vs banca nazionale

Poiché così tanti contenuti sono armonizzati, ogni domanda è classificata in fase di
build (`src/scope.py`) come una tra `universal` (marineria/meteo/primo soccorso) ·
`cevni` (codice delle acque interne) · `colregs` (codice marittimo) · `national`
(norma di legge) · `local` (un singolo specchio d'acqua). Le basi portabili sono
raggruppate tra le banche di **tutti** i Paesi per lingua in bundle additivi
`web/questions.<base>.<lang>.json`, e l'interruttore **National ⟷ Common-core** del
player compone `universal + (cevni | colregs)` per il track della patente attiva. I
bundle nazionali restano **byte-identici** tra le build — un invariante tracciato.
Vedi `docs/scope.md`.

## Il player

`web/` è vanilla JS senza dipendenze. Carica la banca della lingua attiva, legge la
configurazione d'esame dal suo `meta`, ed esegue un **esame** cronometrato e una
modalità **practice** con correzioni con citazione delle fonti. Puoi **studiare per
dominio** (selezionare da quali temi attinge una sessione), commutare il pool
**National ⟷ Common-core**, e la schermata dei risultati scompone il **punteggio per
dominio**. La **countrybar 🇫🇷 / 🇩🇪 / 🇨🇭** commuta tra i player nazionali, ciascuno dei
quali riutilizza lo stesso motore con le proprie regole d'esame. Il player offre
inoltre il **mazzo Anki** e il file **Moodle GIFT** per la lingua attiva come download
con un clic.

### Lingue

L'interfaccia del player è tradotta in **francese, tedesco, italiano e inglese**, e il
contenuto delle domande è costruito per lingua. Laddove la legge ufficiale di un Paese
non sia pubblicata in una lingua (es. inglese in nessun luogo, italiano solo in CH), la
banca è segnalata come **unofficial** oppure ripiega sulla lingua operativa con un
avviso visibile. Le stringhe dell'interfaccia risiedono in `web/i18n.js`; `run.py web`
emette un `questions.<lang>.json` per lingua più un manifesto `languages.json`.

### Esportazioni Anki e Moodle

| Strumento | Comando | Cosa fa |
|------|---------|--------------|
| **Anki** | `python tools/anki.py export [lang]` | Un vero `.apkg` (zip + SQLite, figure incluse, un **sotto-mazzo per tema**) e un `.tsv` modificabile. `import file.tsv --apply` reinserisce le modifiche come bozze **pending**. Solo stdlib. |
| **GIFT** | `python tools/gift.py export [lang]` | Un file **Moodle GIFT**, una `$CATEGORY` per tema, figure incorporate come URI `data:` in base64 così da essere autonomo. Solo stdlib. |

La mappatura Anki è **lossless per il testo modificabile** ma **a struttura bloccata**:
quali opzioni siano corrette, l'immagine e la provenienza restano di proprietà della
banca, quindi una modifica reimportata da Anki/TSV non può mai capovolgere
silenziosamente una risposta — atterra come una bozza `pending` per la rivalutazione.
Tutti gli id dei pacchetti sono derivati dal contenuto (sha1) e gli mtime sono fissati,
così una nuova build è byte-identica.

## Struttura

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

## Test

```bash
for t in tests/test_*.py; do python "$t"; done
```

Tutti offline; non serve alcuna rete né API key.

## Licenza

Gli strumenti in questo repository sono aperti al riutilizzo. Il contenuto acquisito
conserva la propria licenza, registrata per unità e per domanda: il diritto federale
svizzero/francese e il COLREG (USCG) sono di pubblico dominio; gli open data francesi
sono Licence Ouverte / Etalab; il diritto tedesco è §5(1) UrhG e il catalogo ELWIS
§5(2) UrhG (citare www.elwis.de, non modificato); il materiale di matelotage di
Wikipedia è CC BY-SA 4.0; le pagine météo/cantonali sono fonti ufficiali usate con
attribuzione.
