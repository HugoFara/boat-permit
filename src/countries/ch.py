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
from .base import Country, ExamRules, Permit, Region


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
    legal_basis=("Public-domain federal/cantonal law (URG/LDA Art. 5) + openly "
                 "licensed references; theory exam standardised intercantonally "
                 "by the VKS."),
)
