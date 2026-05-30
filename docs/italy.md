# Italia — patente nautica (lavoro futuro, non ancora realizzato)

> **Stato: pianificato, non implementato.** Questo documento descrive *cosa
> richiederebbe* un'estensione Italia. Non esiste oggi alcun modulo paese, permesso
> o banca di domande per l'Italia nel codice. È un segnaposto onesto, non una
> funzionalità.

## Perché non è ancora fatto

L'estensione Italia **non è stata realizzata** perché la normativa nautica italiana è
**molto specifica e stratificata** (codice della nautica da diporto, regolamenti di
attuazione, ordinanze locali delle Capitanerie di porto), e mappare quel quadro su
sorgenti primarie verificate e liberamente riutilizzabili è un lavoro a sé. Verrà
affrontato **se ci sarà domanda** — non prima.

## Cosa esiste oggi (e cosa no)

Nel progetto, `IT` compare **solo come lingua di contenuto**, non come paese: il
diritto svizzero è pubblicato anche in italiano (Ticino), quindi l'esame svizzero
cat-A è già servito in italiano come faccia italofona del contenuto **CH** (vedi
[`switzerland.md`](switzerland.md)). Questo **non** è l'Italia: non c'è alcuna
`patente nautica` italiana, né le sue sorgenti di legge, né il suo formato d'esame.

| | Stato |
|---|---|
| Lingua dei contenuti italiana (UI + banca CH/Ticino) | ✅ esistente |
| Modulo paese `IT` (`src/countries/it.py`) | ❌ non esiste |
| Permessi / esame patente nautica | ❌ non modellati |
| Sorgenti di legge italiane ingerite | ❌ nessuna |

## Cosa richiederebbe un'estensione Italia

Seguendo lo stesso schema di [`france.md`](france.md) e [`germany.md`](germany.md), una
futura estensione Italia dovrebbe stabilire:

- **Tipi di permesso.** La `patente nautica` distingue tipicamente la navigazione
  **entro 12 miglia** dalla costa e **oltre 12 miglia** (senza limiti), per unità a
  motore e/o a vela, più i natanti che ne sono esenti. Il formato d'esame (quiz a
  risposta multipla + prova di carta/carteggio per l'oltre 12 miglia) andrebbe
  verificato sui testi ufficiali, mai a memoria.
- **Sorgenti di legge e licenze.** Da accertare: il **Codice della nautica da diporto**
  (D.lgs. 171/2005) e il suo regolamento di attuazione, il **COLREG/NIPAM** per le
  regole di rotta, la cartografia/maree, le ordinanze delle **Capitanerie di porto** per
  le regole locali. Va verificato il regime di riutilizzo (`normattiva.it` /
  *Gazzetta Ufficiale*: gli atti normativi italiani non sono coperti da diritto
  d'autore, ma redistribuzione e riuso vanno confermati prima dell'ingestione).
- **Nessuna banca di quiz proprietaria.** Come per gli altri paesi, le domande
  andrebbero **derivate dai testi primari** con citazione di provenienza, dietro la
  barriera di revisione — mai copiate da banche commerciali di preparazione.
- **Codici armonizzati condivisi.** Gran parte del contenuto marittimo è COLREG
  (già ingerito tramite lo strato `INT`); l'Italia ne riuserebbe il nucleo comune
  attraverso lo strato **scope** (vedi [`scope.md`](scope.md)).

## In sintesi

Finché non c'è domanda concreta e non è chiarito il quadro normativo/licenze, l'Italia
resta **non in ambito** come paese a sé. La via più breve a contenuti in italiano oggi è
il filone **svizzero/Ticino** già esistente, non un nuovo modulo Italia.
