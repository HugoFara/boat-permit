"""Switzerland — the project's original scope, re-expressed as a Country.

This is a thin adapter: it reuses the existing flat modules unchanged
(:mod:`src.sources`, :mod:`src.themes`, :mod:`src.cantons`, the cat-A/D profiles
in :mod:`src.questions.schema`) so CH behaviour is identical to before the
country dimension existed. Nothing here duplicates logic — it only repackages
those modules into the :class:`Country` shape the pipeline now reads.
"""

from __future__ import annotations

from .. import cantons, sources, themes
from ..questions import schema
from .base import Country, ExamRules, PathStep, Permit, Region


def _exam(cfg: "schema.ExamConfig") -> ExamRules:
    return ExamRules(
        questions=cfg.questions, time_limit_min=cfg.time_limit_min,
        scoring=cfg.scoring, pass_points=cfg.pass_points,
        points_per_question=cfg.points_per_question, total_points=cfg.total_points)


_REGIONS = {
    c.code: Region(code=c.code, name=c.name, time_limit_min=c.time_limit_min,
                   primary=c.leman, note=c.note)
    for c in cantons.CANTONS.values()
}

# Per-category fact note (the threshold that makes the permit mandatory, plus the
# A↔D relationship). Switzerland runs ONE theory exam for every recreational
# category — cat-A and cat-D sit the identical paper — so what actually
# distinguishes the categories is the craft threshold and a separate *practical*
# exam, not the theory. (Confirmed against the cantonal navigation offices / VKS.)
_PERMIT_NOTES = {
    "A": "Bateau à moteur dont la puissance dépasse 6 kW "
         "(4,4 kW sur le lac de Constance).",
    "D": "Bateau à voile dont la surface vélique dépasse 15 m² "
         "(12 m² sur le lac de Constance). Examen théorique identique au "
         "permis A ; seule l’épreuve pratique diffère.",
}

_PERMITS = {
    code: Permit(code=cfg.permis, label=cfg.label, themes=tuple(cfg.themes),
                 exam=_exam(cfg), drive=("sail" if code == "D" else "motor"),
                 note=_PERMIT_NOTES.get(code, ""))
    for code, cfg in schema.PROFILES.items()
}


# --- path-to-permit scaffolding -----------------------------------------------
# The non-theory road to the cat-A/cat-D licence, authored from official sources
# (never from memory): the OCV Genève permit page, ONI art. 82 (RS 747.201.1) as
# stated by the OCN Vaud / Schifffahrtsamt Bern, and the Bern SVSA process page.
# Verified 2026-05-31. No first-aid step: unlike the car licence, no official
# cantonal/federal page lists a first-aid course for the boat permit.
_GE = "https://www.ge.ch/obtenir-permis-conduire-bateaux"
_VD_MED = "https://www.vd.ch/mobilite/navigation/examens-medicaux"
_BE = ("https://www.svsa.sid.be.ch/fr/start/schifffahrt/schiffsfuehrerausweis/"
       "vorgang-schiffsfuehrerausweis-.html")

_PATH: tuple[PathStep, ...] = (
    PathStep(
        code="age", source="OCV — Office cantonal des véhicules, Genève",
        url=_GE, as_of="2026-05-31",
        body={
            "fr": "Âge minimum : 18 ans pour la catégorie A (moteur > 6 kW), "
                  "14 ans pour la catégorie D (voile > 15 m²).",
            "de": "Mindestalter: 18 Jahre für Kategorie A (Motor > 6 kW), "
                  "14 Jahre für Kategorie D (Segel > 15 m²).",
            "it": "Età minima: 18 anni per la categoria A (motore > 6 kW), "
                  "14 anni per la categoria D (vela > 15 m²).",
            "en": "Minimum age: 18 for category A (motor > 6 kW), 14 for "
                  "category D (sail > 15 m²).",
        }),
    PathStep(
        code="medical", source="ONI (RS 747.201.1) art. 82 — OCN Vaud / SVSA Berne",
        url=_VD_MED, as_of="2026-05-31",
        body={
            "fr": "Un test de la vue est rempli sur le formulaire de demande par "
                  "un médecin, opticien ou optométriste reconnu ; il est valable "
                  "24 mois. Il n'est pas exigé si vous détenez déjà un permis de "
                  "conduire (route) ou un permis bateau suisse valable. Un "
                  "certificat médical n'est requis qu'au-delà de 65 ans (ONI art. 82).",
            "de": "Ein Sehtest wird direkt auf dem Gesuch von einer Ärztin/einem "
                  "Arzt, Optiker oder Optometristen ausgefüllt; er ist 24 Monate "
                  "gültig. Nicht nötig, wenn Sie bereits einen gültigen "
                  "Führerausweis (Strasse) oder Schiffsführerausweis besitzen. Ein "
                  "ärztliches Zeugnis ist erst ab 65 Jahren erforderlich (BSV Art. 82).",
            "it": "Un test della vista viene compilato sul modulo di domanda da un "
                  "medico, ottico o optometrista riconosciuto; è valido 24 mesi. "
                  "Non è richiesto se possedete già una licenza di condurre "
                  "(strada) o una licenza nautica svizzera valida. Un certificato "
                  "medico è richiesto solo oltre i 65 anni (ONI art. 82).",
            "en": "An eyesight test is completed on the application form by a "
                  "recognised physician, optician or optometrist; it is valid for "
                  "24 months. It is not required if you already hold a valid Swiss "
                  "(road) driving licence or boat licence. A medical certificate is "
                  "required only above age 65 (ONI art. 82).",
        }),
    PathStep(
        code="practical", source="Schifffahrtsamt Bern (SVSA) — examen pratique VKS",
        url=_BE, as_of="2026-05-31",
        body={
            "fr": "Après la réussite de l'examen théorique, vous disposez de "
                  "24 mois pour passer l'épreuve pratique sur l'eau (env. 60 min). "
                  "C'est la seule épreuve qui diffère entre la cat. A (moteur) et la "
                  "cat. D (voile) — la théorie est identique.",
            "de": "Nach bestandener Theorieprüfung haben Sie 24 Monate Zeit für die "
                  "praktische Prüfung auf dem Wasser (ca. 60 Min.). Nur die "
                  "praktische Prüfung unterscheidet sich zwischen Kat. A (Motor) und "
                  "Kat. D (Segel) — die Theorie ist identisch.",
            "it": "Dopo aver superato l'esame teorico avete 24 mesi per sostenere "
                  "l'esame pratico sull'acqua (ca. 60 min). Solo la prova pratica "
                  "differisce tra cat. A (motore) e cat. D (vela) — la teoria è "
                  "identica.",
            "en": "After passing the theory exam you have 24 months to take the "
                  "on-water practical exam (about 60 min). The practical is the only "
                  "part that differs between cat. A (motor) and cat. D (sail) — the "
                  "theory paper is identical.",
        }),
    PathStep(
        code="application", source="OCV — Office cantonal des véhicules, Genève",
        url=_GE, as_of="2026-05-31",
        body={
            "fr": "Déposez auprès de l'office cantonal de la navigation (à Genève : "
                  "l'OCV) le « formulaire de demande d'un permis de conduire pour "
                  "bateaux », une pièce d'identité valable et une photo passeport. "
                  "L'office délivre ensuite l'autorisation de passer les examens.",
            "de": "Reichen Sie beim kantonalen Schifffahrtsamt (in Genf: OCV) das "
                  "Gesuch um einen Schiffsführerausweis, einen gültigen Ausweis und "
                  "ein Passfoto ein. Das Amt erteilt anschliessend die "
                  "Prüfungszulassung.",
            "it": "Presentate all'ufficio cantonale della navigazione (a Ginevra: "
                  "l'OCV) il modulo di domanda di licenza nautica, un documento "
                  "d'identità valido e una foto formato passaporto. L'ufficio "
                  "rilascia poi l'autorizzazione a sostenere gli esami.",
            "en": "Submit to the cantonal navigation office (in Geneva: the OCV) the "
                  "boat-licence application form, valid ID and a passport photo. The "
                  "office then issues authorisation to sit the exams.",
        }),
    PathStep(
        code="fees", source="OCV — Office cantonal des véhicules, Genève",
        url=_GE, as_of="2026-05-31", volatile=True, region_scope="GE",
        body={
            "fr": "Émoluments (Genève, OCV) : délivrance du permis 150 CHF ; examen "
                  "pratique cat. A/D 140 CHF ; autorisation de passer l'examen dans "
                  "un autre canton 30 CHF. Les tarifs varient d'un canton à l'autre.",
            "de": "Gebühren (Genf, OCV): Ausstellung des Ausweises 150 CHF; "
                  "praktische Prüfung Kat. A/D 140 CHF; Zulassung zur Prüfung in "
                  "einem anderen Kanton 30 CHF. Die Tarife sind kantonal "
                  "unterschiedlich.",
            "it": "Emolumenti (Ginevra, OCV): rilascio della licenza 150 CHF; esame "
                  "pratico cat. A/D 140 CHF; autorizzazione a sostenere l'esame in "
                  "un altro cantone 30 CHF. Le tariffe variano da cantone a cantone.",
            "en": "Fees (Geneva, OCV): licence issuance CHF 150; practical exam "
                  "cat. A/D CHF 140; authorisation to sit the exam in another canton "
                  "CHF 30. Tariffs vary by canton.",
        }),
    PathStep(
        code="validity", source="ONI (RS 747.201.1) art. 82 — OCN Vaud",
        url=_VD_MED, as_of="2026-05-31", volatile=True,
        body={
            "fr": "Le permis n'a pas de durée de validité limitée. Dès 75 ans, un "
                  "contrôle de l'aptitude à conduire est requis tous les 2 ans "
                  "(cat. A/D/E ; ONI art. 82).",
            "de": "Der Ausweis ist unbefristet gültig. Ab 75 Jahren ist alle "
                  "2 Jahre eine Fahreignungskontrolle erforderlich (Kat. A/D/E; "
                  "BSV Art. 82).",
            "it": "La licenza non ha una durata di validità limitata. Dai 75 anni è "
                  "richiesto ogni 2 anni un controllo dell'idoneità alla guida "
                  "(cat. A/D/E; ONI art. 82).",
            "en": "The licence has no fixed expiry. From age 75, a driving-fitness "
                  "check is required every 2 years (cat. A/D/E; ONI art. 82).",
        }),
)


COUNTRY = Country(
    code="CH",
    name="Suisse / Schweiz / Svizzera",
    default_lang="fr",
    langs=("fr", "de", "it", "en"),
    sources=tuple(sources.SOURCES),
    themes=dict(themes.THEMES),
    tagger=themes.tag_theme,
    extension_themes=themes.EXTENSION_THEMES,
    permits=_PERMITS,
    regions=_REGIONS,
    default_region=cantons.DEFAULT_CANTON,
    path=_PATH,
    legal_basis=("Public-domain federal/cantonal law (URG/LDA Art. 5) + openly "
                 "licensed references; theory exam standardised intercantonally "
                 "by the VKS."),
)
