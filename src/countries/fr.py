"""France — the *permis plaisance* (recreational motor-boat licence).

Like :mod:`countries.ch`, this is a thin descriptor that reuses the France content
modules in :mod:`src.fr` (themes, exam profiles, legal sources) rather than
re-declaring them. France is **seed-driven**: it does not use the Fedlex-style
fetch pipeline, so `sources` is empty and the primary law is recorded as
`references` (each question carries its provenance inline — see `src/fr/seed_fr.py`).

French official acts carry no copyright and Légifrance / data.gouv.fr publish under
the Licence Ouverte / Etalab, so the whole bank is freely reusable — the France
analogue of the Swiss public-domain basis. Build it with `python run.py fr`.
"""

from __future__ import annotations

from .base import Country, Permit, ExamRules, PathStep, Region, Reference
from ..fr import themes_fr, exam_fr

LEGAL_BASIS = (
    "Les actes officiels français (lois, décrets, arrêtés) sont exclus du droit "
    "d'auteur ; Légifrance / data.gouv.fr publient sous Licence Ouverte / Open "
    "Licence 2.0 (Etalab). Réutilisation libre, commerciale et non commerciale, "
    "avec attribution."
)

# The national exam format, identical for both base options (Arrêté du 28 sept.
# 2007, art. 1 & 2): 40 single-answer QCM, pass at ≤5 errors (35/40), ~30 min.
def _exam() -> ExamRules:
    return ExamRules(
        questions=exam_fr.QUESTIONS, time_limit_min=exam_fr.TIME_LIMIT_MIN,
        scoring="all_or_nothing", pass_points=exam_fr.PASS_POINTS,
        points_per_question=exam_fr.POINTS_PER_QUESTION,
        total_points=exam_fr.TOTAL_POINTS,
        note="40 QCM à réponse unique ; réussite : 5 fautes maximum (35/40) ; "
             "épreuve valable 18 mois. Examen national, sans variance régionale.")


# Sources are documented but not ingested (France is seed-driven); recorded so the
# legal finding lives in code. Includes the two extensions, which have no QCM bank.
REFERENCES: tuple[Reference, ...] = (
    Reference(
        name="Arrêté du 28 septembre 2007 (permis plaisance — référentiel)",
        url="https://www.legifrance.gouv.fr/loda/id/JORFTEXT000000428843/",
        note="Définit le programme des options côtière (art. 1) et eaux "
             "intérieures (art. 2). Acte officiel, Licence Ouverte."),
    Reference(
        name="Décret n° 2007-1167 du 2 août 2007",
        url="https://www.legifrance.gouv.fr/loda/id/JORFTEXT000000648362/",
        note="Cadre du permis plaisance (puissance > 4,5 kW, âge 16 ans)."),
    Reference(
        name="RIPAM — Règlement international pour prévenir les abordages en mer",
        url="https://www.legifrance.gouv.fr/loda/id/JORFTEXT000000305722/",
        note="Règles de barre, feux et signaux (option côtière)."),
    Reference(
        name="Règlement général de police de la navigation intérieure (RGP/RGPNI)",
        url="https://www.legifrance.gouv.fr/codes/section_lc/LEGITEXT000023086525/LEGISCTA000027232795/",
        note="Implémentation française du CEVNI (option eaux intérieures)."),
    Reference(
        name="Banques de questions des opérateurs agréés (La Poste, Dekra, SGS, "
             "Bureau Veritas)",
        url="https://www.mer.gouv.fr/le-permis-plaisance-permis-de-conduire-les-bateaux-de-plaisance-moteur",
        note="QCM officiels exploités sous contrat confidentiel depuis juin 2022 — "
             "NON réutilisables, jamais ingérés. Les questions du projet sont "
             "dérivées des textes de loi ci-dessus."),
    Reference(
        name="Extension hauturière / Extension grande plaisance eaux intérieures",
        url="https://www.mer.gouv.fr/le-permis-plaisance-permis-de-conduire-les-bateaux-de-plaisance-moteur",
        note="Hauturière : épreuve de carte (pas un QCM). Grande plaisance "
             "(> 20 m) : épreuve pratique. Aucune des deux n'a de banque QCM."),
)


def _tagger(ref: str = "", title: str = "", text: str = "",
            default: str | None = None) -> str:
    """France questions are pre-tagged at authoring time (each seed entry carries
    its theme), so there is no fetch-time tagging to do; return the default."""
    return default or "reglementation"


PERMITS: dict[str, Permit] = {
    "cotiere": Permit(
        code="cotiere", label="Permis plaisance — option côtière",
        themes=themes_fr.OPTION_THEMES["cotiere"], exam=_exam(), drive="motor",
        note="Mer, jusqu'à 6 milles nautiques d'un abri, de jour comme de nuit."),
    "eaux_interieures": Permit(
        code="eaux_interieures", label="Permis plaisance — option eaux intérieures",
        themes=themes_fr.OPTION_THEMES["eaux_interieures"], exam=_exam(), drive="motor",
        note="Rivières, canaux et lacs (RGP, implémentation CEVNI)."),
}

# --- path-to-permit scaffolding ------------------------------------------------
# The non-theory road to the permis plaisance, authored from the official
# mer.gouv.fr brochure "Le permis plaisance" (mai 2023) and the ministry page
# (never from memory). Verified 2026-05-31. Common to both base options (côtière /
# eaux intérieures), so no permit scoping. No first-aid step: none is required.
# Languages fr + en (the bank's two). The mandatory practical TRAINING (3 h 30,
# certified by the centre) replaces a practical exam — there is no on-water test.
_MER = "https://www.mer.gouv.fr/le-permis-plaisance-permis-de-conduire-les-bateaux-de-plaisance-moteur"

PATH: tuple[PathStep, ...] = (
    PathStep(
        code="age", source="mer.gouv.fr — brochure « Le permis plaisance » (mai 2023)",
        url=_MER, as_of="2026-05-31",
        body={
            "fr": "Âge minimum : 16 ans pour s’inscrire dans un établissement de "
                  "formation agréé (options côtière et eaux intérieures).",
            "en": "Minimum age: 16 to enrol at an approved training establishment "
                  "(coastal and inland-waters options).",
        }),
    PathStep(
        code="medical", source="mer.gouv.fr — permis plaisance (aptitude médicale)",
        url=_MER, as_of="2026-05-31",
        body={
            "fr": "Vous devez remplir les conditions d’aptitude médicale : un "
                  "certificat médical de moins de 6 mois (CERFA 14673*01), établi "
                  "par tout médecin (pas de téléconsultation).",
            "en": "You must meet the medical-fitness conditions: a medical "
                  "certificate less than 6 months old (form CERFA 14673*01), issued "
                  "by any doctor (no teleconsultation).",
        }),
    PathStep(
        code="practical", source="mer.gouv.fr — brochure « Le permis plaisance » (mai 2023)",
        url=_MER, as_of="2026-05-31",
        body={
            "fr": "Outre la formation théorique en salle (5 h minimum) sanctionnée "
                  "par le QCM, une formation pratique est obligatoire : "
                  "apprentissage individuel d’au moins 3 h 30, dont 2 h à la barre, "
                  "certifié par le centre de formation (livret d’apprentissage). Il "
                  "n’y a pas d’examen pratique séparé.",
            "en": "Besides the classroom theory training (min. 5 h) assessed by the "
                  "QCM, practical training is mandatory: an individual course of at "
                  "least 3 h 30, of which 2 h at the helm, certified by the training "
                  "centre (logbook). There is no separate practical exam.",
        }),
    PathStep(
        code="application", source="mer.gouv.fr — permis plaisance (inscription)",
        url=_MER, as_of="2026-05-31",
        body={
            "fr": "L’établissement de formation agréé constitue le dossier et "
                  "inscrit le candidat (l’inscription à l’examen théorique peut "
                  "aussi se faire auprès d’un opérateur agréé : La Poste, Dekra, "
                  "SGS, Bureau Veritas). Les services DDTM/DDT instruisent les "
                  "dossiers.",
            "en": "The approved training establishment compiles the file and "
                  "registers the candidate (theory-exam registration can also be "
                  "done with an approved operator: La Poste, Dekra, SGS, Bureau "
                  "Veritas). The DDTM/DDT services process the files.",
        }),
    PathStep(
        code="fees", source="mer.gouv.fr — timbres fiscaux plaisance (mai 2023)",
        url=_MER, as_of="2026-05-31", volatile=True,
        body={
            "fr": "Timbre fiscal de 78 € (droit de délivrance) pour l’option côtière "
                  "ou eaux intérieures, acheté sur timbres.impots.gouv.fr ; frais "
                  "d’inscription à l’examen théorique de 30 € réglés à l’organisme "
                  "agréé. (Extension hauturière : timbre de 38 €.) Le coût de la "
                  "formation en bateau-école s’y ajoute.",
            "en": "A €78 fiscal stamp (issuance fee) for the coastal or "
                  "inland-waters option, bought at timbres.impots.gouv.fr; a €30 "
                  "theory-exam registration fee paid to the approved operator. "
                  "(Offshore extension: €38 stamp.) Boat-school training costs are "
                  "additional.",
        }),
    PathStep(
        code="validity", source="mer.gouv.fr — permis plaisance (validité)",
        url=_MER, as_of="2026-05-31",
        body={
            "fr": "Le permis plaisance est délivré sans limite de durée : aucun "
                  "renouvellement n’est nécessaire.",
            "en": "The permis plaisance is issued with no time limit: no renewal is "
                  "required.",
        }),
)


# The French exam is national — no regional variance (unlike the Swiss cantons).
REGIONS: dict[str, Region] = {
    "national": Region(code="national", name="National (France)", primary=True,
                       note="Examen national identique partout ; opérateurs agréés."),
}
DEFAULT_REGION = "national"


COUNTRY = Country(
    code="FR",
    name="France",
    default_lang="fr",
    langs=("fr", "en"),
    sources=(),                       # seed-driven; provenance is inline in the seed
    themes=dict(themes_fr.FR_THEMES),
    tagger=_tagger,
    permits=PERMITS,
    regions=REGIONS,
    default_region=DEFAULT_REGION,
    references=REFERENCES,
    path=PATH,
    legal_basis=LEGAL_BASIS,
)
