"""Germany — recreational-boating theory exams (Sportbootführerschein system).

Defined natively against :mod:`countries.base`. Two things make Germany a much
richer target than the Swiss original:

* **Federal law is machine-readable and public-domain.** gesetze-im-internet.de
  serves every ordinance as structured XML at ``<slug>/xml.zip`` (the German
  analogue of Fedlex). Federal law is free of copyright under **§5(1) UrhG**.
  These are the ``kind="gii"`` sources below, ingested by the law pipeline.
* **The official question catalogues are very likely free to reuse**
  (§5(2) UrhG — *amtliche Werke*; verbatim + attribution + no modification),
  unlike the off-limits Swiss asa bank. They are recorded as :class:`Reference`
  entries (the legal finding lives in code) but are NOT ingested in this task —
  that is a dedicated follow-up.

Confidence: source URLs/slugs and §5 status are high-confidence. Exam minute
counts and some block minima are school-sourced (medium) — each is flagged in the
relevant ``note`` rather than presented as settled fact, matching the project's
honesty rule for unverified numbers.
"""

from __future__ import annotations

from ..sources import Source
from . import de_themes
from .base import Country, ExamBlock, ExamRules, PathStep, Permit, Reference, Region

# --- 2025–26 reform, still in flux (show as "pending", never as settled law) ---
REFORM_NOTE = (
    "Reform 2025–26 (BMV): Führerscheinpflicht einheitlich ab 11,03 kW (15 PS) "
    "unabhängig von der Antriebsart — die gesonderte 7,5-kW-Grenze für "
    "Elektromotoren soll wieder entfallen. Im Entwurf zudem: Ersatz des amtlichen "
    "SBF durch anerkannte Verbandsscheine (Zielhorizont ~2028). Noch nicht "
    "abgeschlossen — als ausstehend behandeln.")

LEGAL_BASIS = (
    "Bundesrecht (SeeSchStrO, BinSchStrO, KVR, SpFV, RheinSchPV) sowie die "
    "Bodensee-Schifffahrts-Ordnung (BSO, SR 747.223.1) sind gemeinfrei nach "
    "§5(1) UrhG. Die amtlichen ELWIS-Fragenkataloge (SBF See/Binnen) sind sehr "
    "wahrscheinlich amtliche Werke nach §5(2) UrhG: wörtliche Wiedergabe mit "
    "Quellenangabe und ohne Änderung zulässig. Der Bodensee-Fragenkatalog ist "
    "dagegen nicht frei lizenziert — Bodensee-Fragen werden daher aus der BSO "
    "selbst abgeleitet (Clean-Room, Abgleich nur intern).")


# --- federal law (kind="gii": gesetze-im-internet.de/<slug>/xml.zip) -----------
_GII_LICENCE = "Public domain — German federal law (§5(1) UrhG, freely reusable)."

# The Bodensee-Schifffahrts-Ordnung is NOT on gesetze-im-internet.de (it is
# Länder-/Staatsvertragsrecht, DE/AT/CH), but Switzerland consolidates it on
# Fedlex as SR 747.223.1 and serves it as Akoma-Ntoso XML (+ PDF/A annexes) —
# the very same path as the Swiss law spine, so no new parser. A Verordnung is
# public domain (§5(1) UrhG / gemeinfrei). This grounds the *law-seeded* Bodensee
# question set: we author from the BSO and never need the (non-free) BSO question
# catalogue. A reference-copy request has been sent to the rights owners (pending).
_BSO_LICENCE = ("Public domain — Bodensee-Schifffahrts-Ordnung (BSO), SR 747.223.1 "
                "(§5(1) UrhG / gemeinfrei). Trinational DE/AT/CH, konsolidiert über Fedlex.")

SOURCES: list[Source] = [
    Source(
        id="bso", kind="fedlex", lang="de", eli="cc/1976/1338_1338_1338",
        want_pdf=True,
        name="Bodensee-Schifffahrts-Ordnung (BSO), SR 747.223.1",
        url="https://www.fedlex.admin.ch/eli/cc/1976/1338_1338_1338/de",
        default_theme="verkehrsregeln", licence=_BSO_LICENCE),
    Source(
        id="seeschstro", kind="gii", lang="de", gii_slug="seeschstro_1971",
        name="Seeschifffahrtsstraßen-Ordnung (SeeSchStrO)",
        url="https://www.gesetze-im-internet.de/seeschstro_1971/",
        default_theme="verkehrsregeln", licence=_GII_LICENCE),
    Source(
        id="binschstro", kind="gii", lang="de", gii_slug="binschstro_2012",
        name="Binnenschifffahrtsstraßen-Ordnung (BinSchStrO)",
        url="https://www.gesetze-im-internet.de/binschstro_2012/",
        default_theme="verkehrsregeln", licence=_GII_LICENCE),
    Source(
        id="kvr", kind="gii", lang="de", gii_slug="seestro_1972",
        name="Internationale Regeln zur Verhütung von Zusammenstößen auf See (KVR/COLREG)",
        url="https://www.gesetze-im-internet.de/seestro_1972/",
        default_theme="verkehrsregeln", licence=_GII_LICENCE),
    Source(
        id="spfv", kind="gii", lang="de", gii_slug="spfv",
        name="Sportbootführerscheinverordnung (SpFV)",
        url="https://www.gesetze-im-internet.de/spfv/",
        default_theme="recht_dokumente", licence=_GII_LICENCE),
    Source(
        id="rheinschpv", kind="gii", lang="de", gii_slug="rheinschpv_1994",
        name="Rheinschifffahrtspolizeiverordnung (RheinSchPV)",
        url="https://www.gesetze-im-internet.de/rheinschpv_1994/",
        default_theme="verkehrsregeln", licence=_GII_LICENCE),
]


# --- the official question catalogues (INGESTED — see src/questions/elwis.py) --
# The ELWIS Nutzungsbedingungen grant reuse explicitly: content may be reused,
# even commercially, "solange der Inhalt unverändert bleibt und als Quelle
# www.elwis.de angegeben wird" (≈ §5(2) UrhG amtliches Werk). So these are
# ingested verbatim with attribution by `run.py questions --country DE`; the URLs
# here are the canonical landing pages (the ingester discovers the section pages).
_CATALOG_NOTE = ("Amtliches Werk (§5(2) UrhG) — wörtlich + mit Quellenangabe "
                 "(www.elwis.de) + ohne Änderung wiederverwendbar. Ingestiert "
                 "durch run.py questions --country DE (src/questions/elwis.py).")

REFERENCES: tuple[Reference, ...] = (
    Reference(
        name="Amtlicher Fragenkatalog SBF See (≈300 Fragen)",
        url="https://www.elwis.de/DE/Sportschifffahrt/Sportbootfuehrerscheine/"
            "Fragenkatalog-See/Fragenkatalog-See-neu-node.html",
        note=_CATALOG_NOTE),
    Reference(
        name="Amtlicher Fragenkatalog SBF Binnen (≈300 Fragen)",
        url="https://www.elwis.de/DE/Sportschifffahrt/Sportbootfuehrerscheine/"
            "Fragenkatalog-Binnen/Fragenkatalog-Binnen-neu-node.html",
        note=_CATALOG_NOTE),
    Reference(
        name="Fragenkatalog SKS (Sportküstenschifferschein)",
        url="https://www.elwis.de/DE/Sportschifffahrt/Sportbootfuehrerscheine/"
            "Fragenkatalog-SKS/Fragenkatalog-SKS-node.html",
        note=_CATALOG_NOTE + " §5-Status etwas schwächer (DSV/DMYV-Mitautorschaft)."),
    Reference(
        name="Amtlicher Fragenkatalog Bodenseeschifferpatent (Kat. A/D, Stand 01/2023)",
        url="https://www.lrakn.de/service-und-verwaltung/aemter/strassenverkehr+und+schifffahrt/bodenseeschifferpatent",
        note="NICHT frei lizenziert (anders als ELWIS): keine Nachnutzungsfreigabe, "
             "kein amtlicher Volltext-Download; einzige vollständige Gratiskopie ist "
             "privat (© A. Sieber, schifferpatent.org). Daher NICHT ingestiert. Plan: "
             "eigene Fragen aus der BSO (Source 'bso', §5(1) UrhG) ableiten und den "
             "Katalog nur intern zum Abgleich/Divergenz-Filter nutzen (Clean-Room). "
             "Referenzexemplar beim Schifffahrtsamt angefragt — Anfrage versandt, "
             "Antwort der Rechteinhaber ausstehend."),
)


# --- recreational permits ------------------------------------------------------
def _basis(count: int = 7, min_correct: int = 5) -> ExamBlock:
    return ExamBlock("Basisfragen", count, min_correct)


# Bodensee-Schifferpatent theory exam — the Sachgebiete (sections) with their
# per-section question counts and pass minima are the OFFICIAL structure published
# by the Landratsamt Bodenseekreis (Schifferpatentprüfung). Kat A sits the
# Allgemeiner Teil (sections a–g, 86 questions); Kat D adds the two sailing sections
# (h–i, +27 → 113). The pass rule is a minimum in EVERY section with NO compensation
# across sections ("ein Punkteausgleich … ist nicht möglich") — modelled exactly by
# the per-block minima. 1 point per question. This is the exam *structure*; the
# question pool is law-seeded from the BSO separately (see germany-extension memory).
# Source: https://www.bodenseekreis.de/verkehr-wirtschaft/schifffahrt/
#         bodenseeschifferpatent/schifferpatentpruefung/  (verified 2026-05-30)
_BODENSEE_ALLGEMEIN: tuple[ExamBlock, ...] = (
    ExamBlock("Allgemeines, Zulassung, Bau und Ausrüstung", 20, 16),
    ExamBlock("Schallzeichen, Lichterführung, optische Signale", 10, 8),
    ExamBlock("Schifffahrtszeichen", 15, 12),
    ExamBlock("Ausweich- und Fahrregeln", 12, 9),
    ExamBlock("Umweltschutz und Seemannschaft", 12, 9),
    ExamBlock("Wetterkunde und Navigation", 10, 8),
    ExamBlock("Rheinstrecke (Alter Rhein/Seerhein)", 7, 5),
)
_BODENSEE_SEGELN: tuple[ExamBlock, ...] = (
    ExamBlock("Segeln allgemein", 20, 16),
    ExamBlock("Segeln Fahrregeln", 7, 5),
)


PERMITS: dict[str, Permit] = {
    # Federal SBF — mandatory above 11.03 kW (15 PS). Binnen is split by drive.
    "SBF-Binnen-Motor": Permit(
        code="SBF-Binnen-Motor", label="Sportbootführerschein Binnen (Motor)",
        themes=de_themes.PERMIT_THEMES["SBF-Binnen-Motor"], drive="motor",
        exam=ExamRules(questions=30, time_limit_min=45, scoring="blocks",
                       blocks=(_basis(), ExamBlock("Spezifisch Binnen", 23, 18)),
                       note="7 Basis + 23 spezifisch; bestehen: ≥5 Basis & ≥18 spez.")),
    "SBF-Binnen-Motor-Segeln": Permit(
        code="SBF-Binnen-Motor-Segeln",
        label="Sportbootführerschein Binnen (Motor und Segeln)",
        themes=de_themes.PERMIT_THEMES["SBF-Binnen-Motor-Segeln"], drive="motor+sail",
        exam=ExamRules(questions=37, time_limit_min=60, scoring="blocks",
                       blocks=(_basis(), ExamBlock("Spezifisch Binnen", 23, 18),
                               ExamBlock("Spezifisch Segeln", 7, 5)),
                       note="7 Basis + 23 Binnen + 7 Segeln.")),
    "SBF-Binnen-Segeln": Permit(
        code="SBF-Binnen-Segeln", label="Sportbootführerschein Binnen (Segeln)",
        themes=de_themes.PERMIT_THEMES["SBF-Binnen-Segeln"], drive="sail",
        exam=ExamRules(questions=25, time_limit_min=35, scoring="blocks",
                       blocks=(_basis(4, 0), ExamBlock("Spezifisch Binnen", 14, 0),
                               ExamBlock("Spezifisch Segeln", 7, 0)),
                       note="Bestehen: insgesamt ≥20 von 25 (keine festen "
                            "Teilminima); min_correct=0 = kein eigenständiges Minimum.")),
    "SBF-See": Permit(
        code="SBF-See", label="Sportbootführerschein See",
        themes=de_themes.PERMIT_THEMES["SBF-See"], drive="motor+sail",
        exam=ExamRules(questions=30, time_limit_min=60, scoring="blocks",
                       blocks=(_basis(), ExamBlock("Spezifisch See", 23, 18)),
                       note="7 Basis + 23 See, dazu eine Navigationsaufgabe mit "
                            "Seekartenausschnitt (9 Fragen). Minutenzahl näherungsweise.")),
    # Voluntary higher certificates (commercially required only).
    "SKS": Permit(
        code="SKS", label="Sportküstenschifferschein (SKS)",
        themes=de_themes.PERMIT_THEMES["SKS"], drive="motor+sail", mandatory=False,
        exam=ExamRules(questions=30, time_limit_min=90, scoring="blocks",
                       blocks=(ExamBlock("Navigation", 9, 0),
                               ExamBlock("Seerecht", 7, 0),
                               ExamBlock("Wetterkunde", 5, 0),
                               ExamBlock("Seemannschaft", 9, 0)),
                       note="Küste bis 12 sm; setzt SBF See voraus. Plus separate "
                            "Kartenaufgabe. Teilminima/Detailstruktur: mittlere Sicherheit."),
        note="Freiwillig (gewerblich erforderlich)."),
    "SSS": Permit(
        code="SSS", label="Sportseeschifferschein (SSS)",
        themes=de_themes.PERMIT_THEMES["SSS"], drive="motor+sail", mandatory=False,
        exam=ExamRules(questions=0, time_limit_min=0, scoring="blocks",
                       note="Bis 30 sm + Nord-/Ostsee, Mittelmeer u. a. Struktur "
                            "nach DSV-Richtlinien; kein frei veröffentlichter "
                            "amtlicher Katalog gefunden — §5-Wiederverwendung "
                            "unsicher (niedrige Sicherheit)."),
        note="Freiwillig; Katalog-Wiederverwendung rechtlich nicht gesichert."),
    "SHS": Permit(
        code="SHS", label="Sporthochseeschifferschein (SHS)",
        themes=de_themes.PERMIT_THEMES["SHS"], drive="motor+sail", mandatory=False,
        exam=ExamRules(questions=0, time_limit_min=0, scoring="blocks",
                       note="Weltweit/unbegrenzt; setzt SSS voraus. Wie SSS: kein "
                            "frei veröffentlichter amtlicher Katalog — §5 unsicher."),
        note="Freiwillig; Katalog-Wiederverwendung rechtlich nicht gesichert."),
    # Bodensee-Schifferpatent — trinational (DE/AT/CH) regime under the BSO, the
    # German parallel to the project's shared-lake (Lac Léman) origin.
    "Bodensee-A": Permit(
        code="Bodensee-A", label="Bodensee-Schifferpatent Kategorie A (Motor)",
        themes=de_themes.PERMIT_THEMES["Bodensee-A"], drive="motor", track="inland",
        exam=ExamRules(questions=86, time_limit_min=60, scoring="blocks",
                       blocks=_BODENSEE_ALLGEMEIN,
                       note="Allgemeiner Teil: 86 Fragen in 7 Sachgebieten (a–g), "
                            "60 min. Bestehen: Mindestpunktzahl in JEDEM Sachgebiet, "
                            "kein Punkteausgleich. Quelle: Landratsamt Bodenseekreis."),
        note="Trinationales BSO-Patent (DE/AT/CH); Pflicht ab Motorleistung "
             ">4,4 kW. Ausgestellt von den Landratsämtern am See, eigene Prüfung "
             "(nicht der Bund-SBF). Mindestalter 18."),
    "Bodensee-D": Permit(
        code="Bodensee-D", label="Bodensee-Schifferpatent Kategorie D (Segel)",
        themes=de_themes.PERMIT_THEMES["Bodensee-D"], drive="sail", track="inland",
        exam=ExamRules(questions=113, time_limit_min=80, scoring="blocks",
                       blocks=_BODENSEE_ALLGEMEIN + _BODENSEE_SEGELN,
                       note="Allgemeiner Teil (a–g) + Segeln (h–i): 113 Fragen, "
                            "80 min (60 + 20). Selbe Mindestpunktzahl-Regel je "
                            "Sachgebiet, kein Punkteausgleich. Quelle: Landratsamt "
                            "Bodenseekreis."),
        note="Trinationales BSO-Patent (DE/AT/CH); Pflicht ab Segelfläche "
             ">12 m². Ausgestellt von den Landratsämtern am See. Mindestalter 14."),
}


# --- path-to-permit scaffolding ------------------------------------------------
# The non-theory road to the licence, authored from official sources (never from
# memory): the SpFV (gesetze-im-internet.de, §5(1) UrhG), the ELWIS overview, the
# DMYV official fee schedule, and the Landratsamt Bodenseekreis. Verified
# 2026-05-31. German only (this bank ships de). Two regimes, scoped by permit:
# the federal SBF (DMYV/DSV) vs the trinational Bodensee-Schifferpatent
# (Schifffahrtsamt). No first-aid step: no official page lists one (as for CH).
# SKS/SSS/SHS are voluntary advanced certificates with their own prerequisites and
# get no path here — the panel simply stays hidden for them.
_FED = ("SBF-Binnen-Motor", "SBF-Binnen-Motor-Segeln", "SBF-Binnen-Segeln", "SBF-See")
_BSEE = ("Bodensee-A", "Bodensee-D")
_SPFV6 = "https://www.gesetze-im-internet.de/spfv/__6.html"
_SPFV8 = "https://www.gesetze-im-internet.de/spfv/__8.html"
_SPFV = "https://www.gesetze-im-internet.de/spfv/"
_ELWIS_SBF = ("https://www.elwis.de/DE/Sportschifffahrt/Sportbootfuehrerscheine/"
              "Sportbootfuehrerscheine-node.html")
_DMYV_FEES = "https://dmyv-pzrlp.de/gebuehrenseite-neu/"
_LRA_BSEE = ("https://www.bodenseekreis.de/verkehr-wirtschaft/schifffahrt/"
             "bodenseeschifferpatent/schifferpatentpruefung/")

PATH: tuple[PathStep, ...] = (
    # --- federal Sportbootführerschein (DMYV/DSV) ---
    PathStep(
        code="age", source="SpFV §6 Abs. 1 (Sportbootführerscheinverordnung)",
        url=_SPFV6, as_of="2026-05-31", permit_scope=_FED,
        body={"de": "Mindestalter: 16 Jahre für Motorantrieb, 14 Jahre für "
                    "Segeln (SpFV §6 Abs. 1)."}),
    PathStep(
        code="medical", source="SpFV §6 Abs. 2 + Anlage 2", url=_SPFV6,
        as_of="2026-05-31", permit_scope=_FED,
        body={"de": "Erforderlich ist ein ärztlicher Tauglichkeitsnachweis. Die "
                    "Sehschärfe muss auf beiden Augen zusammen oder auf dem besseren "
                    "Auge ≥ 0,8 betragen (mit oder ohne Sehhilfe), geprüft nach "
                    "DIN 58220 (SpFV §6 Abs. 2, Anlage 2)."}),
    PathStep(
        code="practical", source="SpFV §8 + Anlage 4", url=_SPFV8,
        as_of="2026-05-31", permit_scope=_FED,
        body={"de": "Nach der Theorieprüfung folgt die praktische Prüfung: "
                    "Pflichtmanöver (u. a. Rettungsmanöver/Mann-über-Bord, An- und "
                    "Ablegen), weitere Manöver je nach Antriebsart sowie Knoten "
                    "(SpFV §8, Anlage 4)."}),
    PathStep(
        code="application", source="ELWIS — Sportbootführerscheine (BMDV)",
        url=_ELWIS_SBF, as_of="2026-05-31", permit_scope=_FED,
        body={"de": "Zulassung, Prüfung und Ausstellung erfolgen über die vom BMDV "
                    "beauftragten Verbände: Deutscher Motoryachtverband (DMYV) oder "
                    "Deutscher Segler-Verband (DSV)."}),
    PathStep(
        code="fees", source="DMYV — amtliche Prüfungsgebühren (Stand 01/2023)",
        url=_DMYV_FEES, as_of="2026-05-31", volatile=True, permit_scope=_FED,
        body={"de": "Amtliche Prüfungsgebühren (DMYV/DSV): SBF See 148,38 € "
                    "(Theorie 47,56 + Praxis 47,62 + Erteilung 29,82 + Zulassung "
                    "23,38); SBF Binnen Motor 130,78 €, Segeln 127,84 €. Die Kurs-/"
                    "Ausbildungskosten der Bootsschule kommen hinzu (je nach Anbieter "
                    "rund 300–1000 €)."}),
    PathStep(
        code="validity", source="SpFV (Verordnung über das Führen von Sportbooten)",
        url=_SPFV, as_of="2026-05-31", permit_scope=_FED,
        body={"de": "Der Sportbootführerschein ist unbefristet gültig; eine "
                    "Erneuerung ist nicht erforderlich (der ärztliche "
                    "Tauglichkeitsnachweis kann hingegen befristet sein)."}),
    # --- trinational Bodensee-Schifferpatent (Schifffahrtsamt, DE/AT/CH) ---
    PathStep(
        code="age", source="Landratsamt Bodenseekreis — Schifferpatent",
        url=_LRA_BSEE, as_of="2026-05-31", permit_scope=_BSEE,
        body={"de": "Mindestalter: 18 Jahre für Kategorie A (Motor), 14 Jahre für "
                    "Kategorie D (Segel)."}),
    PathStep(
        code="medical", source="Landratsamt Bodenseekreis — Schifferpatent",
        url=_LRA_BSEE, as_of="2026-05-31", permit_scope=_BSEE,
        body={"de": "Ein ärztliches Gutachten über die Tauglichkeit ist vorzulegen "
                    "(Formular des Schifffahrtsamts)."}),
    PathStep(
        code="practical", source="Landratsamt Bodenseekreis — Schifferpatent",
        url=_LRA_BSEE, as_of="2026-05-31", permit_scope=_BSEE,
        body={"de": "Praktische Prüfung mit Motormanövern (Anlegen, Ablegen, "
                    "Mann-über-Bord) sowie — Kat. D — Segelmanövern und Knoten "
                    "(u. a. Palstek, Webleinstek, Schotstek)."}),
    PathStep(
        code="application", source="Landratsamt Bodenseekreis — Schifffahrtsamt",
        url=_LRA_BSEE, as_of="2026-05-31", permit_scope=_BSEE,
        body={"de": "Das Bodensee-Schifferpatent wird vom Schifffahrtsamt des "
                    "Landratsamts (am See) ausgestellt — eigene Prüfung, nicht der "
                    "Bund-SBF."}),
)


# --- regional variance ---------------------------------------------------------
REGIONS: dict[str, Region] = {
    "national": Region(code="national", name="Bundesweit (SBF See/Binnen)",
                       primary=True,
                       note="Föderal einheitlich nach SpFV; keine Länder-Varianz."),
    "bodensee": Region(code="bodensee", name="Bodensee (BSO, DE/AT/CH)",
                       note="Eigenes trinationales Patent-Regime; ersetzt am See "
                            "den Bund-SBF (niedrigere Leistungsschwelle 4,4 kW)."),
}
DEFAULT_REGION = "national"


COUNTRY = Country(
    code="DE",
    name="Deutschland",
    default_lang="de",
    langs=("de",),
    sources=tuple(SOURCES),
    themes=dict(de_themes.THEMES),
    tagger=de_themes.tag_theme,
    extension_themes=de_themes.EXTENSION_THEMES,
    permits=PERMITS,
    regions=REGIONS,
    default_region=DEFAULT_REGION,
    references=REFERENCES,
    path=PATH,
    legal_basis=LEGAL_BASIS,
    # BSO-seeded prose questions belong to the Bodensee-Schifferpatent Sachgebiete.
    prose_block_for=de_themes.bodensee_block_for,
)
