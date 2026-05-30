"""Stage 2 — dispatch each fetched source to its source-specific parser.

One parser per source kind; each returns a flat list of KnowledgeUnit. This
stage is pure (no network): it reads the raw cache + manifest written by fetch.
"""

from __future__ import annotations

import json
import os

from .sources import Source, SOURCES
from .schema import KnowledgeUnit
from .parsers import akn, wikipedia, html_generic

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")

_PARSERS = {
    "fedlex": akn.parse,
    "wikipedia": wikipedia.parse,
    "html": html_generic.parse,
}


def _manifest(source_id: str, lang: str = "fr") -> dict:
    sub = source_id if lang == "fr" else os.path.join(source_id, lang)
    with open(os.path.join(RAW_DIR, sub, "manifest.json"), encoding="utf-8") as fh:
        return json.load(fh)


def parse_source(src: Source, lang: str = "fr") -> list[KnowledgeUnit]:
    return _PARSERS[src.kind](src, _manifest(src.id, lang))


def parse_all(sources: list[Source] | None = None,
              langs: tuple[str, ...] = ("fr",)) -> dict[str, list[KnowledgeUnit]]:
    """Parse the selected sources in each requested language. FR parses every
    source; non-FR languages parse only the law (fedlex) sources, whose other
    official-language manifestations were fetched into data/raw/<id>/<lang>/.
    Keyed by '<id>' for FR (legacy) and '<id>@<lang>' otherwise."""
    out: dict[str, list[KnowledgeUnit]] = {}
    for src in (sources or SOURCES):
        for lang in langs:
            if lang != "fr" and src.kind != "fedlex":
                continue
            key = src.id if lang == "fr" else f"{src.id}@{lang}"
            out[key] = parse_source(src, lang)
    return out
