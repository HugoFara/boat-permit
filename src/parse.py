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


def _manifest(source_id: str) -> dict:
    with open(os.path.join(RAW_DIR, source_id, "manifest.json"), encoding="utf-8") as fh:
        return json.load(fh)


def parse_source(src: Source) -> list[KnowledgeUnit]:
    return _PARSERS[src.kind](src, _manifest(src.id))


def parse_all(sources: list[Source] | None = None) -> dict[str, list[KnowledgeUnit]]:
    return {src.id: parse_source(src) for src in (sources or SOURCES)}
