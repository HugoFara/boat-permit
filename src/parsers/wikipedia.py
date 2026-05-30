"""Parser for Wikipedia (matelotage) pages fetched via the MediaWiki parse API.

Each page becomes a handful of `prose_section` units (one per substantive H2
section), plus a representative diagram as an image asset. Wikipedia chrome —
maintenance banners, infoboxes, edit links, references, navboxes — is stripped.
Content is CC BY-SA 4.0; the licence + page revision travel into provenance.
"""

from __future__ import annotations

import json
import os
import re

from bs4 import BeautifulSoup

from ..schema import KnowledgeUnit, Asset, make_id
from ..sources import Source
from .. import themes

# Sections that carry no study value.
_SKIP_SECTIONS = {
    "notes et références", "références", "voir aussi", "liens externes",
    "bibliographie", "articles connexes", "annexes", "sources", "notes",
}
# CSS selectors for chrome to remove before reading text.
_STRIP_SELECTORS = (
    "table.infobox", "table.infobox_v2", ".navbox", ".bandeau", ".bandeau-container",
    ".hatnote", ".homonymie", ".metadata", ".mw-editsection", "sup.reference",
    ".reference", ".noprint", "style", "script", ".mw-empty-elt", ".thumbcaption",
    ".gallerybox .thumb + *", "table.wikitable.mw-collapsible",
)


def _clean(soup: BeautifulSoup) -> None:
    for sel in _STRIP_SELECTORS:
        for el in soup.select(sel):
            el.decompose()


def _is_content_image(img) -> bool:
    src = img.get("src", "")
    if not src.startswith(("http", "//")):
        return False
    # skip UI chrome / tiny icons
    if re.search(r"(Info_Simple|Edit-clear|disambig|Logo_|Commons-logo|"
                 r"Wiktionary|Loudspeaker|Crystal|Nuvola|/\d{1,2}px-)", src):
        return False
    w = img.get("width")
    try:
        if w and int(w) < 60:
            return False
    except ValueError:
        pass
    return True


def _abs_url(src: str) -> str:
    return ("https:" + src) if src.startswith("//") else src


def parse(src: Source, manifest: dict) -> list[KnowledgeUnit]:
    base = os.path.join(os.path.dirname(__file__), "..", "..")
    units: list[KnowledgeUnit] = []

    for page_title, info in manifest["pages"].items():
        if "path" not in info:
            continue
        revid = info.get("revid", "")
        page_url = f"https://fr.wikipedia.org/wiki/{page_title.replace(' ', '_')}"
        prov = dict(source_id=src.id, source_name=src.name, source_url=page_url,
                    retrieved=manifest["retrieved"], legal_version=str(revid),
                    licence=src.licence)
        soup = BeautifulSoup(open(os.path.join(base, info["path"]), encoding="utf-8").read(),
                             "html.parser")
        _clean(soup)
        root = soup.select_one(".mw-parser-output") or soup

        # representative diagram = first real content image on the page
        lead_asset_url = ""
        for img in root.select("img"):
            if _is_content_image(img):
                lead_asset_url = _abs_url(img["src"])
                break

        # Walk children, grouping paragraphs under their preceding H2.
        section = "Présentation"
        buf: list[str] = []

        def flush(section_name: str, paras: list[str], with_image: bool):
            text = re.sub(r"\s+", " ", " ".join(paras)).strip()
            if len(text) < 80 or section_name.lower() in _SKIP_SECTIONS:
                return
            ref = f"Matelotage — {page_title} : {section_name}"
            assets = []
            if with_image and lead_asset_url:
                assets = [Asset(type="image", path=lead_asset_url,
                                caption=f"{page_title} ({section_name})")]
            units.append(KnowledgeUnit(
                id=make_id(src.id, ref), theme="matelotage", kind="prose_section",
                ref=ref, title=f"{page_title} — {section_name}", text=text,
                assets=assets, cross_refs=[], **prov))

        first_section_done = False
        for el in root.find_all(["h2", "h3", "p"], recursive=True):
            if el.name in ("h2", "h3"):
                flush(section, buf, with_image=not first_section_done)
                first_section_done = True
                buf = []
                section = el.get_text(" ", strip=True).replace("[modifier | modifier le code]", "").strip()
            elif el.name == "p":
                t = el.get_text(" ", strip=True)
                if t and not t.lower().startswith(("pour les articles homonymes",
                                                   "l'introduction de cet article",
                                                   "cet article")):
                    buf.append(t)
        flush(section, buf, with_image=not first_section_done)

    return units
