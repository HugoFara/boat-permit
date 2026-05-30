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

    # Annex-level citation map: which articles cite "annexe N" (by number/roman),
    # so each annex figure can deterministically link back to its governing
    # article(s). Citations are annex-level in the law — finer per-figure links
    # are a semantic-matching job left to the (reviewed) question stage.
    annex_cites: dict[str, list[str]] = {}
    art_by_num: dict[str, str] = {}
    for u in units:
        if u.kind != "article":
            continue
        for m in re.finditer(r"annexe\s+([0-9]+[a-z]*|[ivx]+)\b", u.text or "", re.I):
            annex_cites.setdefault(m.group(1).lower(), []).append(u.id)
        am = re.match(r"art\.\s*([0-9]+[a-z]*)", u.ref.split(" ", 1)[1] if " " in u.ref else "", re.I)
        if am:
            art_by_num[am.group(1).lower()] = u.id

    units.extend(_parse_annexes(src, root, images, prefix, prov, annex_cites, art_by_num))
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


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).replace("\xa0", " ").strip()


def _p_texts(el) -> list[str]:
    """Normalized text of each <p> under `el`, in order, footnotes stripped.
    Reading per-<p> (instead of one raw itertext join) is what stops adjacent
    cells gluing — e.g. <p>let. b</p><p>ballon vert</p> stays two strings, not
    the run-together "let. bballon vert"."""
    clone = etree.fromstring(etree.tostring(el))
    for note in clone.iter(AKN + "authorialNote"):
        note.getparent().remove(note)
    return [t for p in clone.iter(AKN + "p") if (t := _norm("".join(p.itertext())))]


# A paragraph that is only a reference label ("let. b", "ch. 4", "al. 2") is a
# legal back-reference, not the figure's description — kept as a locator, not caption.
_REF_LABEL = re.compile(r"^(let\.|ch\.|al\.|lettre|chiffre)(\s|$)", re.I)
# Inline article citation inside an annex legend cell (RNL annexes do this), e.g.
# "IV.2 Art. 42" -> article 42. These give precise per-figure article links.
_ART_REF = re.compile(r"\bArt\.\s*(\d+[a-z]*)", re.I)
_NUM_ONLY = re.compile(r"^\d+$")
# Locator fragments that pollute a caption: abbreviations ("art. 24", "al. 1",
# "let. c") and dotted section codes ("II.A.4", "A.10", "IV.2"). Stripped so the
# caption keeps only the human description; the section code is case-sensitive so
# it can't eat lowercase prose.
_LOC_ABBR = re.compile(
    r"\b(?:art|al|ch)\.\s*\d+[a-z]?\b|\blet\.\s*[a-z]+\b"
    r"|\bchiffre\s*\d+\b|\blettre\s*[a-z]+\b", re.I)
_LOC_SECTION = re.compile(r"\b[A-Z]{1,4}(?:\.\w+)+")


def _clean_desc(p: str) -> str:
    """Strip legal locator fragments from a description paragraph. Returns the
    leftover prose (empty if the paragraph was nothing but a citation)."""
    s = _LOC_ABBR.sub("", _LOC_SECTION.sub("", p))
    if s == p:
        return p.strip()                      # no locator present — leave untouched
    return re.sub(r"\s{2,}", " ", re.sub(r"^[\s,;.:()«»–—-]+", "", s)).strip(" ,;.:()«»–—-")


def _has_words(paras: list[str]) -> bool:
    """True if any paragraph carries a real word (≥3 letters) — i.e. actual
    description text, not a bare index/connector like "1a" or "ou"."""
    return any(re.search(r"[A-Za-zÀ-ÿ]{3,}", p) for p in paras)


def _figure_parts(td, img, row) -> tuple[str, str, list[str], str]:
    """For one image, return (legend, ref_label, article_refs, description):
      - legend: the index printed next to the image (Layout B/C: "<img> 13" -> "13";
        Layout A images carry none -> "");
      - ref_label: any "let. b / ch. 4" cross-reference text (a locator);
      - article_refs: article numbers cited in the legend cell ("Art. 42" -> "42");
      - description: the human caption (the answer text for a signal question).
    Bare legend numbers are dropped (they belong to *some* image in the cell, not
    to the description). The description comes from the image's own cell (Layout A)
    or, when that cell holds only image(s)+number(s), from the sibling text cell."""
    # The legend index sits in each image's own paragraph ("<img> 1a"); exclude
    # every image legend in the cell so a sibling image's index can't pose as text.
    legends = {_norm("".join(i.getparent().itertext())) for i in td.iter(AKN + "img")}
    paras = [p for p in _p_texts(td) if p not in legends and not _NUM_ONLY.match(p)]
    if not _has_words(paras):     # Layout B/C, or a bare connector cell ("ou")
        sib_paras: list[str] = []
        for sib in row.findall(AKN + "td"):
            if sib is td or sib.find(".//" + AKN + "img") is not None:
                continue
            sib_paras += [p for p in _p_texts(sib) if not _NUM_ONLY.match(p)]
        if _has_words(sib_paras):
            paras = sib_paras
    refs, arts, desc = [], [], []
    for p in paras:
        arts += _ART_REF.findall(p)
        if _REF_LABEL.match(p):           # a pure "let. b / al. 2" locator
            refs.append(p)
            continue
        cleaned = _clean_desc(p)          # drop any "art. 24, al. 1" / "II.A.4" debris
        if _has_words([cleaned]):
            desc.append(cleaned)
    legend = _norm("".join(img.getparent().itertext()))        # "13" or ""
    return legend, " ".join(refs), arts, "; ".join(desc)


def _annex_token(annex_num: str) -> str:
    """The citable token of an annex label ("Annexe 1a" -> "1a", "Annexe III" ->
    "iii"), matching how articles cite it."""
    m = re.search(r"annexe\s+([0-9]+[a-z]*|[ivx]+)", annex_num, re.I)
    return m.group(1).lower() if m else ""


def _parse_annexes(src: Source, root, images: dict, prefix: str, prov: dict,
                   annex_cites: dict[str, list[str]], art_by_num: dict[str, str]
                   ) -> list[KnowledgeUnit]:
    """Walk annex <doc> elements and emit one annex_figure unit per referenced
    figure, captioned from its own table cell (per-image, not per-row). Each
    figure links to its governing article — by the explicit "Art. N" in its
    legend cell when present, else to whichever article(s) cite its annex — and
    carries its annex legend index. These hold the signal/buoyage diagrams."""
    units: list[KnowledgeUnit] = []
    for doc in root.iter(AKN + "doc"):
        preface = doc.find(AKN + "preface")
        annex_num = _block(preface, "num") if preface is not None else ""
        annex_num = re.split(r"\s{2,}|Mise à jour|Introduit", annex_num)[0].strip() or "Annexe ?"
        annex_title = _block(preface, "title") if preface is not None else ""
        if not annex_title:
            h = doc.find(".//" + AKN + "heading")
            annex_title = "".join(h.itertext()).strip() if h is not None else ""
        cites = annex_cites.get(_annex_token(annex_num), [])

        seen_in_annex = 0
        for tr in doc.iter(AKN + "tr"):
            # Visit image-bearing cells in document order so each figure is
            # captioned from its own cell, not the whole row.
            for td in tr.findall(AKN + "td"):
                row_imgs = [im for im in td.iter(AKN + "img")
                            if images.get(im.get("src"), {}).get("bytes", 0) >= _MIN_FIGURE_BYTES]
                for im in row_imgs:
                    seen_in_annex += 1
                    meta = images[im.get("src")]
                    asset_path = _stable_asset_path(src.id, meta["path"])
                    legend, ref_label, arts, desc = _figure_parts(td, im, tr)
                    ref = f"{prefix} {annex_num} – fig. {seen_in_annex}"
                    caption = desc or f"{annex_num} – {annex_title}".strip(" –")
                    locator = ", ".join(
                        x for x in (annex_num, f"ch. {legend}" if legend else "", ref_label)
                        if x)
                    text = f"{locator} — {desc}" if desc else locator
                    # Prefer the precise article(s) named in the legend cell;
                    # fall back to whichever article(s) cite this whole annex.
                    cross = [art_by_num[n] for n in arts if n in art_by_num] or list(cites)
                    theme = themes.tag_theme(ref=ref, title=annex_title, text=desc,
                                             default="signalisation")
                    units.append(KnowledgeUnit(
                        id=make_id(src.id, ref), theme=theme, kind="annex_figure",
                        ref=ref, title=f"{annex_num} — {annex_title}".strip(" —"),
                        text=text,
                        assets=[Asset(type="image", path=asset_path, caption=caption)],
                        cross_refs=cross, **prov))
    return units


def _stable_asset_path(source_id: str, raw_rel_path: str) -> str:
    """Asset path published into the KB (under data/assets/<source>/<file>).
    The normalize stage copies the raw image to this path."""
    fname = os.path.basename(raw_rel_path)
    return os.path.join("data", "assets", source_id, fname)
