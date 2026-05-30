"""Parser for gesetze-im-internet.de law XML (German federal ordinances).

The German federal portal serves each ordinance as a ``<slug>/xml.zip`` using a
custom DTD (gii-norm 1.01): a ``<dokumente>`` root holding repeated ``<norm>``
elements (no XML namespace). The first norm is a framing header (law title,
issue date, "Stand"); each subsequent norm is one provision identified by
``<enbez>`` ("§ 1", "Anlage 1") with a ``<titel>`` heading and a
``<textdaten>/<text>/<Content>`` body. Figures are ``<IMG SRC=…>`` referencing
files bundled in the same zip.

Each provision becomes one article-level :class:`KnowledgeUnit`, tagged to the
German exam taxonomy. Mirrors :mod:`parsers.akn` (the Swiss Akoma Ntoso parser)
in spirit; the German law is single-language, so tagging uses the German tagger
directly rather than the cross-language propagation the Swiss path relies on.
"""

from __future__ import annotations

import os
import re

from lxml import etree

from ..countries import de_themes
from ..schema import Asset, KnowledgeUnit, make_id
from ..sources import Source

# Images below this size are inline glyphs/spacers, not real diagrams.
_MIN_FIGURE_BYTES = 250


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).replace("\xa0", " ").strip()


def _content_text(norm) -> str:
    """Flattened body text of a norm, footnote apparatus removed. Joining on the
    text nodes (not a single itertext concat) keeps adjacent list terms/cells
    from gluing together (e.g. a definition term and its explanation)."""
    content = norm.find("textdaten/text/Content")
    if content is None:
        return ""
    clone = etree.fromstring(etree.tostring(content))
    for tag in ("Footnotes", "FnArea"):
        for el in list(clone.iter(tag)):
            parent = el.getparent()
            if parent is not None:
                parent.remove(el)
    return _clean(" ".join(clone.itertext()))


def _law_abbrev(root) -> str:
    """The ordinance's citation abbreviation (jurabk), e.g. 'SeeSchStrO'."""
    for norm in root.iter("norm"):
        j = norm.findtext("metadaten/jurabk")
        if j and j.strip():
            return j.strip()
    return ""


def parse(src: Source, manifest: dict, tagger=None) -> list[KnowledgeUnit]:
    # `tagger` is the country's theme classifier; defaults to the German one
    # (gii is German federal law), so passing country.tagger is a no-op for DE.
    tag_theme = tagger or de_themes.tag_theme
    xml_path = os.path.join(os.path.dirname(__file__), "..", "..",
                            manifest["files"]["xml"]["path"])
    root = etree.parse(xml_path).getroot()
    images = manifest["files"].get("images", {})
    lang = manifest.get("lang", "de")
    abbrev = _law_abbrev(root)

    prov = dict(source_id=src.id, source_name=src.name, source_url=src.url,
                retrieved=manifest["retrieved"],
                legal_version=manifest.get("legal_version", ""), licence=src.licence,
                lang=lang)

    units: list[KnowledgeUnit] = []
    for norm in root.iter("norm"):
        md = norm.find("metadaten")
        enbez = _clean(md.findtext("enbez") or "") if md is not None else ""
        if not enbez:                      # framing/header norm — no provision label
            continue
        title = _clean(md.findtext("titel") or "")
        body = _content_text(norm)
        if not body and not title:
            continue

        ref = f"{abbrev} {enbez}".strip()
        unit_id = make_id(src.id, ref, lang)

        assets: list[Asset] = []
        for i, im in enumerate(norm.iter("IMG"), start=1):
            fname = os.path.basename(im.get("SRC") or "")
            meta = images.get(fname)
            if not meta or meta.get("bytes", 0) < _MIN_FIGURE_BYTES:
                continue
            caption = _clean(im.get("alt") or "") or f"{ref} – Abbildung {i}"
            assets.append(Asset(type="image",
                                path=_asset_path(src.id, meta["path"], lang),
                                caption=caption))

        theme = tag_theme(ref=ref, title=title, text=body,
                          default=src.default_theme)
        units.append(KnowledgeUnit(
            id=unit_id, theme=theme, kind="article", ref=ref,
            title=title, text=body, assets=assets, **prov))
    return units


def _asset_path(source_id: str, raw_rel_path: str, lang: str = "de") -> str:
    """Where the figure is published in the KB. Non-FR languages are namespaced
    (data/assets/<source>/<lang>/<file>) so the normalize stage copies the raw
    image from the matching data/raw/<source>/<lang>/images/ cache."""
    fname = os.path.basename(raw_rel_path)
    sub = source_id if lang == "fr" else os.path.join(source_id, lang)
    return os.path.join("data", "assets", sub, fname)
