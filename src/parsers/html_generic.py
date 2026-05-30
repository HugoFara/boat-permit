"""Generic parser for prose web pages (MétéoSuisse winds, SISL storm signals,
Geneva cantonal consignes).

These have no shared structure, so we strip chrome, then do a flat document-order
walk grouping paragraphs/list-items under their preceding heading into
`prose_section` units. Nav/login/footer headings are skipped; each unit is themed
from its text and carries full provenance + the source's licence note.
"""

from __future__ import annotations

import json
import os
import re

from bs4 import BeautifulSoup

from ..schema import KnowledgeUnit, make_id
from ..sources import Source
from .. import themes

_STRIP_TAGS = ("script", "style", "nav", "header", "footer", "aside", "form",
               "button", "noscript", "svg")
# Heading text (lowercased) that signals navigation / boilerplate, not content.
_SKIP_HEADINGS = re.compile(
    r"^(login|recherche|navigation|menu|actualit[eé]s|partager|connexion|"
    r"clés d.accès|top bar|services|secrétariat|liens utiles|cookies|"
    r"newsletter|contact|suivez|réseaux sociaux|plan du site|aide)\b")
_MIN_SECTION_CHARS = 80


def _root(soup: BeautifulSoup):
    for sel in ("[role=main]", "main", "article", ".field--name-body", "#content"):
        el = soup.select_one(sel)
        if el is not None and len(el.get_text(strip=True)) > 400:
            return el
    return soup.body or soup


def parse(src: Source, manifest: dict) -> list[KnowledgeUnit]:
    base = os.path.join(os.path.dirname(__file__), "..", "..")
    html = open(os.path.join(base, manifest["files"]["html"]["path"]),
                encoding="utf-8", errors="replace").read()
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(list(_STRIP_TAGS)):
        tag.decompose()
    root = _root(soup)

    page_url = manifest.get("final_url") or src.url
    prov = dict(source_id=src.id, source_name=src.name, source_url=page_url,
                retrieved=manifest["retrieved"],
                legal_version=manifest.get("legal_version", ""), licence=src.licence)

    units: list[KnowledgeUnit] = []
    section = ""
    buf: list[str] = []

    def flush(name: str, paras: list[str]):
        text = re.sub(r"\s+", " ", " ".join(paras)).strip()
        if len(text) < _MIN_SECTION_CHARS:
            return
        if name and _SKIP_HEADINGS.match(name.lower()):
            return
        label = name or "Présentation"
        ref = f"{src.name.split('—')[0].strip()} : {label}"
        theme = themes.tag_theme(ref=ref, title=label, text=text,
                                 default=src.default_theme)
        units.append(KnowledgeUnit(
            id=make_id(src.id, ref), theme=theme, kind="prose_section",
            ref=ref, title=label, text=text, assets=[], cross_refs=[], **prov))

    for el in root.find_all(["h1", "h2", "h3", "h4", "p", "li"], recursive=True):
        if el.name in ("h1", "h2", "h3", "h4"):
            flush(section, buf)
            buf = []
            section = el.get_text(" ", strip=True)
        else:
            t = el.get_text(" ", strip=True)
            if t:
                buf.append(t)
    flush(section, buf)

    # De-dup identical sections (some pages repeat blocks across components).
    seen, deduped = set(), []
    for u in units:
        key = (u.title, u.text[:120])
        if key not in seen:
            seen.add(key)
            deduped.append(u)
    return deduped
