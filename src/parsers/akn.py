"""Parser for Fedlex Akoma Ntoso 3.0 acts (ONI, RNL).

Turns one act into article-level knowledge units. For each <article>: number,
title (heading), clean body text (footnotes stripped, structure flattened),
the chapter path for context, and any annex figures referenced inside it become
image assets + their own `annex_figure` units linked back to the article.
"""

from __future__ import annotations

import os
import re

from lxml import etree

from ..schema import KnowledgeUnit, Asset, make_id
from ..sources import Source
from .. import themes

AKN = "{http://docs.oasis-open.org/legaldocml/ns/akn/3.0}"

# Images below this size are inline spacers/glyphs, not real diagrams.
_MIN_FIGURE_BYTES = 250


def _localname(el) -> str:
    return etree.QName(el).localname


def _text(el) -> str:
    """Flattened visible text of an element, footnotes (authorialNote) removed,
    whitespace normalized."""
    clone = etree.fromstring(etree.tostring(el))
    for note in clone.iter(AKN + "authorialNote"):
        note.getparent().remove(note)
    raw = "".join(clone.itertext())
    return re.sub(r"[ \t]*\n[ \t\n]*", " ", raw).replace("\xa0", " ").strip()


def _chapter_path(article) -> str:
    """Human chapter context from the enclosing <level> num/heading elements."""
    parts: list[str] = []
    p = article.getparent()
    while p is not None and _localname(p) != "akomaNtoso":
        if _localname(p) == "level":
            h = p.find(AKN + "heading")
            if h is not None:
                ht = "".join(h.itertext()).strip()
                # headings sometimes carry a trailing footnote sentence — trim it
                ht = re.split(r"\s{2,}|Introduit par|Nouvelle teneur", ht)[0].strip()
                if ht:
                    parts.append(ht)
        p = p.getparent()
    return " › ".join(reversed(parts))


def _article_number(article) -> str:
    num = article.find(AKN + "num")
    if num is None:
        return article.get("eId", "")
    clone = etree.fromstring(etree.tostring(num))
    for note in clone.iter(AKN + "authorialNote"):
        note.getparent().remove(note)
    t = re.sub(r"\s+", " ", "".join(clone.itertext())).strip()
    # Keep only the "Art. 23" / "Art. 25a" token; drop any trailing footnote prose.
    m = re.match(r"Art\.?\s*([0-9]+[a-z]*)", t, flags=re.I)
    if m:
        return f"art. {m.group(1)}"
    return re.sub(r"^Art\.?\s*", "art. ", t, flags=re.I).strip()


def parse(src: Source, manifest: dict) -> list[KnowledgeUnit]:
    xml_path = os.path.join(os.path.dirname(__file__), "..", "..",
                            manifest["files"]["xml"]["path"])
    tree = etree.parse(xml_path)
    root = tree.getroot()
    images = manifest["files"].get("images", {})

    prefix = "ONI" if src.id == "oni" else ("RNL" if src.id == "rnl" else src.id.upper())
    prov = dict(source_id=src.id, source_name=src.name, source_url=src.url,
                retrieved=manifest["retrieved"],
                legal_version=manifest.get("legal_version", ""), licence=src.licence)

    units: list[KnowledgeUnit] = []
    for article in root.iter(AKN + "article"):
        number = _article_number(article)           # "art. 23"
        heading_el = article.find(AKN + "heading")
        title = "".join(heading_el.itertext()).strip() if heading_el is not None else ""
        chapter = _chapter_path(article)

        # Body = article text minus the leading "Art. N" + heading echo.
        body = _text(article)
        lead = (number.replace("art. ", "Art. ") + title)
        if body.startswith(lead):
            body = body[len(lead):].strip()

        ref = f"{prefix} {number}"
        article_id = make_id(src.id, ref)
        theme = themes.tag_theme(ref=ref, title=f"{chapter} {title}", text=body,
                                 default=src.default_theme)

        # Figures referenced inside this article.
        assets: list[Asset] = []
        cross: list[str] = []
        for i, img in enumerate(article.iter(AKN + "img"), start=1):
            ref_src = img.get("src")
            meta = images.get(ref_src)
            if not meta or meta.get("bytes", 0) < _MIN_FIGURE_BYTES:
                continue
            asset_path = _stable_asset_path(src.id, meta["path"])
            caption = (img.get("alt") or "").strip() or f"{ref} – figure {i}"
            assets.append(Asset(type="image", path=asset_path, caption=caption))
            # Each figure also becomes its own retrievable annex_figure unit.
            fig_ref = f"{ref} – fig. {i}"
            fig_id = make_id(src.id, fig_ref)
            cross.append(fig_id)
            units.append(KnowledgeUnit(
                id=fig_id, theme="signalisation", kind="annex_figure",
                ref=fig_ref, title=title or "Figure",
                text=f"Figure de l’{prefix} {number}" + (f" — {title}" if title else ""),
                assets=[Asset(type="image", path=asset_path, caption=caption)],
                cross_refs=[article_id], **prov))

        full_title = f"{chapter} — {title}" if chapter and title else (title or chapter)
        units.append(KnowledgeUnit(
            id=article_id, theme=theme, kind="article", ref=ref,
            title=full_title, text=body, assets=assets, cross_refs=cross, **prov))

    units.extend(_parse_annexes(src, root, images, prefix, prov))
    return units


def _block(preface, name: str) -> str:
    """Text of a preface <block name=...>, footnotes stripped."""
    for blk in preface.iter(AKN + "block"):
        if blk.get("name") == name:
            clone = etree.fromstring(etree.tostring(blk))
            for note in clone.iter(AKN + "authorialNote"):
                note.getparent().remove(note)
            return re.sub(r"\s+", " ", "".join(clone.itertext())).strip()
    return ""


def _row_caption(tr) -> str:
    """Caption for a figure row: text of the row's cells (the figure number cell
    plus the description cell), footnotes stripped, normalized."""
    clone = etree.fromstring(etree.tostring(tr))
    for note in clone.iter(AKN + "authorialNote"):
        note.getparent().remove(note)
    parts = []
    for td in clone.iter(AKN + "td"):
        txt = re.sub(r"\s+", " ", "".join(td.itertext())).strip()
        if txt:
            parts.append(txt)
    return " — ".join(parts)


def _parse_annexes(src: Source, root, images: dict, prefix: str, prov: dict
                   ) -> list[KnowledgeUnit]:
    """Walk annex <doc> elements and emit one annex_figure unit per referenced
    figure, captioned from its table row. These carry the signal/buoyage diagrams."""
    units: list[KnowledgeUnit] = []
    for doc in root.iter(AKN + "doc"):
        preface = doc.find(AKN + "preface")
        annex_num = _block(preface, "num") if preface is not None else ""
        annex_num = re.split(r"\s{2,}|Mise à jour|Introduit", annex_num)[0].strip() or "Annexe ?"
        annex_title = _block(preface, "title") if preface is not None else ""
        if not annex_title:
            h = doc.find(".//" + AKN + "heading")
            annex_title = "".join(h.itertext()).strip() if h is not None else ""

        seen_in_annex = 0
        # rows that contain images, in document order
        for tr in doc.iter(AKN + "tr"):
            row_imgs = [im for im in tr.iter(AKN + "img")
                        if images.get(im.get("src"), {}).get("bytes", 0) >= _MIN_FIGURE_BYTES]
            if not row_imgs:
                continue
            caption = _row_caption(tr)
            for im in row_imgs:
                seen_in_annex += 1
                meta = images[im.get("src")]
                asset_path = _stable_asset_path(src.id, meta["path"])
                ref = f"{prefix} {annex_num} – fig. {seen_in_annex}"
                cap = caption or f"{annex_num} – {annex_title}"
                theme = themes.tag_theme(ref=ref, title=annex_title, text=cap,
                                         default="signalisation")
                units.append(KnowledgeUnit(
                    id=make_id(src.id, ref), theme=theme, kind="annex_figure",
                    ref=ref, title=f"{annex_num} — {annex_title}".strip(" —"),
                    text=cap,
                    assets=[Asset(type="image", path=asset_path, caption=cap)],
                    cross_refs=[], **prov))
    return units


def _stable_asset_path(source_id: str, raw_rel_path: str) -> str:
    """Asset path published into the KB (under data/assets/<source>/<file>).
    The normalize stage copies the raw image to this path."""
    fname = os.path.basename(raw_rel_path)
    return os.path.join("data", "assets", source_id, fname)
