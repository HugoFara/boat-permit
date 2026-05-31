# Deutschland — Sportbootführerschein (Erweiterung des Lerntools)

Dieses Dokument beschreibt den Deutschland-Teil des boating-licence-Lerntools. Die
juristische und redaktionelle Grenze ist **dieselbe wie beim Schweizer Kern**: Jede
Frage ist *aus Primärquellen abgeleitet* und trägt eine Quellenangabe zurück zum
Text, aus dem sie stammt. Eine Besonderheit gegenüber der Schweiz: Für die
bundesweiten SBF-Prüfungen existiert ein **amtlicher Fragenkatalog (ELWIS)**, der
unter **§5(2) UrhG** wörtlich nachgenutzt werden darf — dieser wird unverändert
übernommen statt neu formuliert (siehe unten).

## Führerschein-Arten

Deutschland regelt die Sportschifffahrt über das **Sportbootführerschein-System**
(SBF). Die Führerscheinpflicht greift ab **11,03 kW (15 PS)** Motorleistung
(bundesweit, SpFV). Das Tool modelliert die folgenden Scheine (`src/countries/de.py`):

| Code | Schein | Antrieb | Pflicht? |
|------|--------|---------|----------|
| `SBF-Binnen-Motor` | Sportbootführerschein Binnen (Motor) | Motor | ja (ab 11,03 kW) |
| `SBF-Binnen-Segeln` | Sportbootführerschein Binnen (Segeln) | Segel | ja |
| `SBF-Binnen-Motor-Segeln` | Sportbootführerschein Binnen (Motor und Segeln) | Motor + Segel | ja |
| `SBF-See` | Sportbootführerschein See | Motor + Segel | ja (Seeschifffahrtsstraßen) |
| `SKS` | Sportküstenschifferschein | Motor + Segel | freiwillig (gewerblich erforderlich) |
| `SSS` | Sportseeschifferschein | Motor + Segel | freiwillig |
| `SHS` | Sporthochseeschifferschein | Motor + Segel | freiwillig |
| `Bodensee-A` | Bodensee-Schifferpatent Kategorie A (Motor) | Motor | ja am Bodensee (ab 4,4 kW) |
| `Bodensee-D` | Bodensee-Schifferpatent Kategorie D (Segel) | Segel | ja am Bodensee (ab 12 m² Segelfläche) |

Die freiwilligen höheren Scheine (`SSS`, `SHS`) sind als Katalogeinträge erfasst,
haben aber noch keine verlässlich frei lizenzierte Fragenquelle (`questions=0`).

## Prüfungsstruktur — block­basierte Bewertung

Anders als die Schweizer Punktwertung werden die deutschen SBF-Prüfungen
**blockweise** bewertet: Es gilt ein Mindestbestehen **pro Block**, ohne
Punkteausgleich zwischen den Blöcken. Modelliert in `src/questions/schema.py`
(`grade_exam_blocks`); die Blöcke je Schein stehen in `src/countries/de.py`:

| Schein | Blöcke | Bestehen |
|--------|--------|----------|
| `SBF-Binnen-Motor` | 7 Basisfragen + 23 Spezifisch Binnen | ≥5 Basis **und** ≥18 spez. |
| `SBF-Binnen-Motor-Segeln` | 7 Basis + 23 Binnen + 7 Segeln | je Block |
| `SBF-Binnen-Segeln` | 4 Basis + 14 Binnen + 7 Segeln | insgesamt ≥20/25 (keine festen Teilminima) |
| `SBF-See` | 7 Basis + 23 Spezifisch See | ≥5 Basis **und** ≥18 spez.; dazu eine Navigationsaufgabe mit Seekartenausschnitt (9 Fragen) |

> Hinweis: Einige Minutenzahlen und Teilminima stammen aus Schulungsquellen
> (mittlere Sicherheit) und sind im jeweiligen `note`-Feld als solche markiert —
> nicht als gesicherte Tatsache dargestellt (Ehrlichkeitsregel des Projekts).

## Sachgebiete (Themen-Taxonomie)

Die SBF-Prüfungen testen eine Handvoll Sachgebiete. Jede eingelesene Rechts-Einheit
wird regelbasiert und nachvollziehbar getaggt (`src/countries/de_themes.py`):

`definitionen` · `verkehrsregeln` · `schifffahrtszeichen` · `lichter_signale` ·
`wetterkunde` · `seemannschaft` · `navigation` · `gezeiten` · `umweltschutz` ·
`recht_dokumente`

Nur die regeltragenden Themen erhalten Einheiten aus dem **Gesetzestext**
(Verkehrsregeln, Zeichen, Lichter/Signale, Definitionen, Umwelt, Recht). Die
übrigen — `wetterkunde`, `seemannschaft`, `navigation`, `gezeiten` — sind
Katalog-/Lehrthemen ohne Verordnungstext (EXTENSION-Themen), sodass ein reiner
Gesetzes-Build legitim keine Einheiten dafür hat und die Normalize-Stufe nicht warnt.
Binnen nutzt den Inland-Kern; See ergänzt Küstennavigation + Gezeiten.

## Rechtsquellen & Lizenzen

### Bundesrecht — gemeinfrei (§5(1) UrhG)

`gesetze-im-internet.de` liefert jede Verordnung als strukturiertes XML unter
`<slug>/xml.zip` (das deutsche Pendant zu Fedlex). Bundesrecht ist nach **§5(1)
UrhG** urheberrechtsfrei. `run.py build --country DE` liest (`kind="gii"`):

| `id` | Quelle | Standard-Thema |
|------|--------|----------------|
| `seeschstro` | Seeschifffahrtsstraßen-Ordnung (SeeSchStrO) | verkehrsregeln |
| `binschstro` | Binnenschifffahrtsstraßen-Ordnung (BinSchStrO) | verkehrsregeln |
| `kvr` | Internationale Regeln zur Verhütung von Zusammenstößen auf See (KVR/COLREG) | verkehrsregeln |
| `spfv` | Sportbootführerscheinverordnung (SpFV) | recht_dokumente |
| `rheinschpv` | Rheinschifffahrtspolizeiverordnung (RheinSchPV) | verkehrsregeln |
| `bso` | Bodensee-Schifffahrts-Ordnung (BSO, SR 747.223.1) | verkehrsregeln |

Die **BSO** liegt nicht auf gesetze-im-internet.de (Länder-/Staatsvertragsrecht
DE/AT/CH), wird aber von der Schweiz über **Fedlex** als Akoma-Ntoso-XML
konsolidiert (SR 747.223.1) — derselbe Pfad wie die Schweizer Rechtsbasis, also
kein neuer Parser. Betonnung ist **IALA-Region A** (rot an Backbord bei Einfahrt).

### Amtlicher Fragenkatalog ELWIS — nachnutzbar (§5(2) UrhG)

Anders als die gesperrte Schweizer asa-Bank sind die amtlichen **ELWIS**-Fragenkataloge
für SBF See/Binnen nachnutzbar: Die ELWIS-Nutzungsbedingungen gestatten die Nachnutzung
(auch kommerziell) *„solange der Inhalt unverändert bleibt und als Quelle www.elwis.de
angegeben wird"* (amtliches Werk nach **§5(2) UrhG**). `run.py questions --country DE`
liest beide Kataloge **wörtlich** ein (`src/questions/elwis.py`, ≈515 Fragen nach
Entdoppelung der geteilten Basisfragen 1–72), jede Frage einem Thema + Prüfungsblock
zugeordnet, die Schilder-/Lichterabbildungen als Assets, und jede Frage trägt die
§5-Quellenangabe in ihrer Herkunft. Weil die Nachnutzung an **Unveränderlichkeit**
gebunden ist, ist die deutsche Bank **deutschsprachig** (keine Übersetzung) und die
Antwortoptionen werden nur **deterministisch für die Anzeige umsortiert**, nie
umformuliert.

### Bodensee-Fragenkatalog — NICHT frei (Clean-Room)

Der amtliche Bodensee-Fragenkatalog (Kat. A/D) ist — anders als ELWIS — **nicht frei
lizenziert**: keine Nachnutzungsfreigabe, kein amtlicher Volltext-Download. Er wird
daher **nicht** eingelesen. Stattdessen werden Bodensee-Fragen aus der **BSO selbst**
abgeleitet (Quelle `bso`, §5(1) UrhG); der Katalog dient höchstens **intern** zum
Abgleich/Divergenz-Filter (Clean-Room-Muster). Ein Referenzexemplar wurde beim
Schifffahrtsamt angefragt (Antwort der Rechteinhaber ausstehend).

## Bodensee-Schifferpatent — das trinationale Regime

Das **Bodensee-Schifferpatent** ist das deutsche Gegenstück zum
Léman-Ursprung des Projekts: ein eigenes trinationales (DE/AT/CH) Regime unter der
BSO, das am See den Bund-SBF ersetzt (niedrigere Schwelle 4,4 kW). Es hat eine
**eigene Prüfung**, ausgestellt von den Landratsämtern am See. Die Prüfungsstruktur
(`_BODENSEE_ALLGEMEIN` / `_BODENSEE_SEGELN` in `src/countries/de.py`) ist die offizielle
Gliederung des Landratsamts Bodenseekreis:

- **Kategorie A (Motor):** Allgemeiner Teil — 86 Fragen in 7 Sachgebieten (a–g), 60 min.
- **Kategorie D (Segel):** Allgemeiner Teil + Segeln (h–i) — 113 Fragen, 80 min.

Bestehen heißt: Mindestpunktzahl in **jedem** Sachgebiet, **kein Punkteausgleich**
(„ein Punkteausgleich … ist nicht möglich") — exakt über die Teilminima je Block
modelliert.

## Reform 2025–26 (ausstehend, kein geltendes Recht)

Eine BMV-Reform ist in Arbeit und wird als *pending* geführt, nicht als gesichertes
Recht (`countries/de.py:REFORM_NOTE`): Führerscheinpflicht einheitlich ab 11,03 kW
unabhängig von der Antriebsart (Wegfall der gesonderten 7,5-kW-Grenze für
Elektromotoren); im Entwurf zudem der Ersatz des amtlichen SBF durch anerkannte
Verbandsscheine (Zielhorizont ~2028). Noch nicht abgeschlossen.

## Fragen-Scope & der gemeinsame Kern

Deutschland nimmt an der gemeinsamen **scope**-Schicht teil (`src/scope.py`, siehe
[`scope.md`](scope.md)). Jede Frage wird beim Build über das Prüfungs-`block`-Feld
einer Basis im Regime-Baum zugeordnet: `spezifisch_see` → `colregs`,
`spezifisch_binnen` → `cevni`, dazu `universal` (Seemannschaft/Wetter/Umwelt) und
`national` (Recht/Dokumente). Eine Bodensee-Frage scopt `local` (eigenes BSO-Regime,
nicht portabel). Der deutsche See-Katalog speist so den **global gepoolten
COLREGS-Kern**, auf den auch andere Länder zugreifen — sprachgebunden, also für
französische Lernende erst nach Übersetzung nutzbar. Der `web/de/`-Player erhält einen
`core`-Block, der auf die übergeordneten globalen Bundles zeigt.

## Build

```bash
python run.py build     --country DE      # Bundesrecht (gii) + BSO (Fedlex) → KB
python run.py questions --country DE      # ELWIS-Kataloge wörtlich einlesen
python run.py web                          # Bank + Assets → web/de/ bündeln
python -m http.server -d web 8000          # http://localhost:8000/de/
```

Im Player öffnet **🇩🇪 Deutschland** den `web/de/`-Bundle, wo ein **Schein-Auswähler**
die echte **blockstrukturierte Prüfung** steuert (Papier je Block zusammengesetzt,
nach Teilminima bewertet). Siehe `src/countries/de.py` (Registry-Deskriptor),
`src/countries/de_themes.py` (Taxonomie + Tagger), `src/questions/elwis.py`
(Katalog-Einleser) und `src/scope.py` (deutsche Klassifizierer-Branch).
