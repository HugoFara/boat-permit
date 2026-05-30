"""Stage 2 — dispatch each fetched source to its source-specific parser.

One parser per source kind; each returns a flat list of KnowledgeUnit. This
stage is pure (no network): it reads the raw cache + manifest written by fetch.
"""

from __future__ import annotations

import json
import os

from .sources import Source, SOURCES
from .schema import KnowledgeUnit
from .parsers import akn, gii, wikipedia, html_generic, colreg

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")

_PARSERS = {
    "fedlex": akn.parse,
    "gii": gii.parse,
    "wikipedia": wikipedia.parse,
    "html": html_generic.parse,
    "pdf": colreg.parse,
}
# Law kinds whose act is parsed once per requested language (per-lang raw cache).
_PER_LANG_KINDS = {"fedlex", "gii"}


def _manifest(source_id: str, lang: str = "fr") -> dict:
    sub = source_id if lang == "fr" else os.path.join(source_id, lang)
    with open(os.path.join(RAW_DIR, sub, "manifest.json"), encoding="utf-8") as fh:
        return json.load(fh)


def parse_source(src: Source, lang: str = "fr", tagger=None) -> list[KnowledgeUnit]:
    # law (fedlex/gii): the requested language's manifestation lives under a
    # per-lang subdir for non-fr (data/raw/<id>/<lang>/); language-specific
    # sources (wikipedia/html) are cached flat in their own language. The law
    # parsers (the _PER_LANG_KINDS) accept the country's theme tagger; the
    # others tag structurally and ignore it.
    if src.kind in _PER_LANG_KINDS:
        return _PARSERS[src.kind](src, _manifest(src.id, lang), tagger=tagger)
    return _PARSERS[src.kind](src, _manifest(src.id))


def parse_all(sources: list[Source] | None = None,
              langs: tuple[str, ...] = ("fr",), tagger=None) -> dict[str, list[KnowledgeUnit]]:
    """Parse the selected sources for the requested languages. Law (fedlex) acts
    are parsed once per language; language-specific sources (Wikipedia/HTML) are
    parsed only when their own `lang` is requested. Keyed '<id>' (fr law /
    lang-specific source) or '<id>@<lang>' (non-fr law). `tagger` is the country's
    theme classifier, threaded into the law parsers (defaults to per-parser Swiss/
    German tagger when None, so CH/DE builds are unchanged)."""
    out: dict[str, list[KnowledgeUnit]] = {}
    for src in (sources or SOURCES):
        if src.kind in _PER_LANG_KINDS:
            for lang in langs:
                key = src.id if lang == "fr" else f"{src.id}@{lang}"
                out[key] = parse_source(src, lang, tagger=tagger)
        elif src.lang in langs:
            out[src.id] = parse_source(src)
    return out
