"""Country-model dataclasses — pure data, no logic.

A :class:`Country` bundles everything that varies between national exams: which
sources ground it, the exam-theme taxonomy + the tagger that sorts units into it,
the recreational-permit catalogue, the regional variance (cantons / Länder / a
shared-lake regime) and the legal basis for reuse. The Swiss instance
(:mod:`countries.ch`) is a thin adapter over the original flat modules; new
countries (:mod:`countries.de`) are defined natively against these types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass(frozen=True)
class ExamBlock:
    """One scored section of a block-based exam (German SBF style): ``count``
    questions are drawn and at least ``min_correct`` must be right to pass."""
    name: str
    count: int
    min_correct: int


@dataclass(frozen=True)
class ExamRules:
    """How a sitting is assembled and graded. Two scoring regimes are modelled:

    * ``all_or_nothing`` — the Swiss VKS point system; ``pass_points`` of
      ``total_points`` are needed (per-question all-or-nothing).
    * ``blocks`` — the German SBF system; each :class:`ExamBlock` carries its own
      pass minimum and the candidate must clear every block.
    """
    questions: int
    time_limit_min: int
    scoring: str                                   # "all_or_nothing" | "blocks"
    pass_points: int | None = None
    points_per_question: int | None = None
    total_points: int | None = None
    blocks: tuple[ExamBlock, ...] = ()
    note: str = ""


@dataclass(frozen=True)
class Permit:
    """A recreational permit category and the exam that grants it."""
    code: str                                      # stable key, e.g. "A", "SBF-See"
    label: str
    themes: tuple[str, ...]                        # which taxonomy themes it draws on
    exam: ExamRules
    drive: str = ""                                # "motor" | "sail" | "motor+sail"
    track: str = ""                                # "inland" | "maritime"; "" ⇒ inferred
    mandatory: bool = True                         # legally required vs voluntary
    note: str = ""


@dataclass(frozen=True)
class Region:
    """A within-country variance unit: a Swiss canton, a German Bundesland, or a
    special regime such as a shared lake. ``time_limit_min`` overrides the exam
    timer where a region sets its own; ``None`` means it inherits the default."""
    code: str
    name: str
    time_limit_min: int | None = None
    primary: bool = False                          # the project's headline scope
    note: str = ""


@dataclass(frozen=True)
class Reference:
    """A source that is documented and legally cleared but not (yet) ingested —
    e.g. an official question catalogue. Records the reuse note so the legal
    finding lives in code, ready for a later ingestion task."""
    name: str
    url: str
    note: str = ""


@dataclass(frozen=True)
class Country:
    """The full description of one country's exam domain."""
    code: str                                      # ISO 3166-1 alpha-2 ("CH", "DE")
    name: str
    default_lang: str
    langs: tuple[str, ...]
    sources: tuple                                 # tuple[sources.Source, ...]
    themes: dict                                   # {theme_id: human label}
    tagger: Callable                               # (ref, title, text, default) -> id
    permits: dict                                  # {code: Permit}
    regions: dict                                  # {code: Region}
    default_region: str
    extension_themes: frozenset = frozenset()      # scaffolded ahead of a source
    references: tuple = ()                         # tuple[Reference, ...]
    legal_basis: str = ""
    # Maps a prose-drafted question's theme -> the exam-block id it belongs to,
    # for countries whose prose pool feeds a block-structured exam (DE: the BSO
    # prose seeds the Bodensee-Schifferpatent Sachgebiete). None -> prose carries
    # no block (CH point-scored, INT sourcing-only).
    prose_block_for: Callable | None = None

    def region_manifest(self) -> list[dict]:
        """Regions for the player picker, primary scope first then by code."""
        ordered = sorted(self.regions.values(), key=lambda r: (not r.primary, r.code))
        return [{"code": r.code, "name": r.name, "time_limit_min": r.time_limit_min,
                 "primary": r.primary, "note": r.note} for r in ordered]
