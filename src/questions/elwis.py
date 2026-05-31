"""Ingest the official German SBF question catalogues (ELWIS Fragenkataloge).

Germany's amtliche Fragenkataloge are, unlike the off-limits Swiss asa bank,
**freely reusable**. ELWIS's Nutzungsbedingungen grant it explicitly: *"Alle über
ELWIS veröffentlichten Informationen dürfen übernommen und auch kommerziell
nachgenutzt werden, solange der Inhalt unverändert bleibt und als Quelle
www.elwis.de angegeben wird."* — reuse (even commercial) is permitted **on two
conditions: the content stays unchanged + www.elwis.de is attributed** (an
amtliches Werk under §5(2) UrhG). So we ingest the questions **verbatim**, carry
the attribution on every `Provenance`, and never translate or reword them.

Two things follow from "unverändert":
  * The German bank is German-only (translation would be a modification).
  * Each option's *text* is stored byte-for-byte. We only permute the *display
    order* — the catalogue publishes "answer a is always correct", so storing the
    published order would leak the answer. Reordering presentation is not a change
    of content, and the shuffle is **deterministic** (seeded from the question id)
    so rebuilds reproduce the bank exactly.

Source format: the catalogues live as HTML section pages (Basisfragen,
Spezifische Fragen …, Navigationsaufgaben). Each question is a numbered ``<p>``
followed by an ``<ol class="elwisOL-lowerLiteral">`` of four ``<li>`` options,
with figures as ``<img>`` (sign/lights graphics under ``…/Grafiken/…``). `fetch`
caches the pages + figures; `parse` is offline; `ingest` runs both and dedups the
Basisfragen 1–72 that See and Binnen share.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import random
import re
import urllib.parse
from dataclasses import dataclass

import requests
from lxml import html as _html

from .schema import Choice, Provenance, Question, make_question_id
from ..countries import de_themes

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_RAW_DIR = os.path.join(_ROOT, "data", "raw", "elwis")
_ASSET_DIR = os.path.join(_ROOT, "data", "assets", "elwis")
_HEADERS = {"User-Agent": "boating-licence-study/0.1 (multi-country aggregator; "
                          "personal study tool)"}

GENERATOR = "elwis:fragenkatalog"

# The reuse grant, recorded verbatim-in-spirit on every question's provenance.
LICENCE = ("© Wasserstraßen- und Schifffahrtsverwaltung des Bundes (WSV/ELWIS). "
           "Frei nachnutzbar, auch kommerziell, sofern unverändert und mit "
           "Quellenangabe www.elwis.de (ELWIS-Nutzungsbedingungen; amtliches Werk "
           "nach §5(2) UrhG).")


@dataclass(frozen=True)
class Catalogue:
    id: str             # "binnen" | "see"
    label: str          # "SBF Binnen" — for the provenance source string
    version: str        # catalogue "Stand", e.g. "2023-08"
    as_of: str          # ISO date the catalogue applies from
    index_url: str      # the page listing the section links
    url: str            # canonical landing page (provenance)


_ELWIS = ("https://www.elwis.de/DE/Sportschifffahrt/Sportbootfuehrerscheine")

CATALOGUES: dict[str, Catalogue] = {
    "binnen": Catalogue(
        id="binnen", label="SBF Binnen", version="2023-08", as_of="2023-08-01",
        index_url=f"{_ELWIS}/Fragenkatalog-Binnen/Fragenkatalog-Binnen-neu-page.html",
        url=f"{_ELWIS}/Fragenkatalog-Binnen/Fragenkatalog-Binnen-neu-node.html"),
    "see": Catalogue(
        id="see", label="SBF See", version="2023-08", as_of="2023-08-01",
        index_url=f"{_ELWIS}/Fragenkatalog-See/Fragenkatalog-See-neu-page.html",
        url=f"{_ELWIS}/Fragenkatalog-See/Fragenkatalog-See-neu-node.html"),
}

# Section-name keyword -> exam-block id. Order matters: "Binnen"/"See"/"Segeln"
# are checked before the generic case. The block id is what the player groups on
# for block-based grading; the German theme (separate) drives study-by-domain.
_BLOCK_BY_KEYWORD: list[tuple[str, str]] = [
    ("basisfragen", "basis"),
    ("spezifische fragen binnen", "spezifisch_binnen"),
    ("spezifische fragen see", "spezifisch_see"),
    ("spezifische fragen segeln", "segeln"),
    ("navigationsaufgaben", "navigation"),
]

# Ties the permit exam structure in countries/de.py (whose ExamBlocks are named
# in German) to the block ids the ingested questions carry — so a permit's
# per-block pass minima can be matched against the question pool for grading.
BLOCK_NAME_TO_ID: dict[str, str] = {
    "Basisfragen": "basis",
    "Spezifisch Binnen": "spezifisch_binnen",
    "Spezifisch See": "spezifisch_see",
    "Spezifisch Segeln": "segeln",
}

# A reasonable theme fallback per block when no keyword rule in the stem fires.
_DEFAULT_THEME_BY_BLOCK = {
    "basis": "verkehrsregeln", "spezifisch_binnen": "verkehrsregeln",
    "spezifisch_see": "verkehrsregeln", "segeln": "seemannschaft",
    "navigation": "navigation",
}

_NUM_STEM = re.compile(r"^\s*(\d+)\.\s+(.*)$", re.S)


def _block_for(text: str) -> str:
    low = (text or "").lower()
    for kw, block in _BLOCK_BY_KEYWORD:
        if kw in low:
            return block
    return ""


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).replace("\xa0", " ").strip()


def _seed(s: str) -> int:
    """Process-stable seed (NOT builtin hash(), which is salted per run)."""
    return int(hashlib.sha1(s.encode()).hexdigest()[:8], 16)


def _is_figure(src: str) -> bool:
    """A content figure (sign/lights graphic), not site chrome (icons/SVG)."""
    s = (src or "").lower()
    return ("/grafiken/" in s or "/anlage-" in s) and not s.endswith(".svg")


def _asset_basename(src: str) -> str:
    """Stable filename for a figure URL, dropping the query (?__blob=…&v=…)."""
    return os.path.basename(urllib.parse.urlparse(src).path)


# --------------------------------------------------------------------------
# fetch: cache the section pages + their figures (network)
# --------------------------------------------------------------------------

def _get(url: str) -> requests.Response:
    r = requests.get(url, headers=_HEADERS, timeout=60)
    r.raise_for_status()
    return r


def _section_links(index_html: str) -> list[tuple[str, str]]:
    """(block_id, section_url) for each catalogue section, discovered from the
    index page's internal links rather than hardcoded paths."""
    root = _html.fromstring(index_html)
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for a in root.iter("a"):
        href = a.get("href") or ""
        block = _block_for(a.text_content())
        if block and href and block not in seen:
            seen.add(block)
            out.append((block, href))
    return out


def fetch(cat: Catalogue, force: bool = False) -> dict:
    """Cache a catalogue's section pages under data/raw/elwis/<cat>/<version>/ and
    its figures under data/assets/elwis/<cat>/de/. Returns a manifest mirroring the
    gii fetcher's shape (sections + an images map keyed by basename)."""
    raw = os.path.join(_RAW_DIR, cat.id, cat.version)
    assets = os.path.join(_ASSET_DIR, cat.id, "de")
    os.makedirs(raw, exist_ok=True)
    os.makedirs(assets, exist_ok=True)
    manifest_path = os.path.join(raw, "manifest.json")
    if os.path.exists(manifest_path) and not force:
        with open(manifest_path, encoding="utf-8") as fh:
            return json.load(fh)

    sections: list[dict] = []
    images: dict[str, dict] = {}
    for block, url in _section_links(_get(cat.index_url).text):
        html = _get(url).text
        page = os.path.join(raw, f"{block}.html")
        with open(page, "w", encoding="utf-8") as fh:
            fh.write(html)
        sections.append({"block": block, "url": url,
                         "path": os.path.relpath(page, _ROOT)})
        for im in _html.fromstring(html).iter("img"):
            src = im.get("src") or ""
            if not _is_figure(src):
                continue
            base = _asset_basename(src)
            if base in images:
                continue
            full = urllib.parse.urljoin(url, src)
            local = os.path.join(assets, base)
            with open(local, "wb") as fh:
                fh.write(_get(full).content)
            images[base] = {"path": os.path.relpath(local, _ROOT), "url": full}

    manifest = {
        "catalogue": cat.id, "version": cat.version, "as_of": cat.as_of,
        "retrieved": _dt.date.today().isoformat(), "canonical_url": cat.url,
        "sections": sections, "images": images,
    }
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    return manifest


# --------------------------------------------------------------------------
# parse: cached HTML -> Question objects (offline, deterministic)
# --------------------------------------------------------------------------

def _figure_path(img_el, images: dict) -> str | None:
    """Repo-relative asset path for an <img>, looked up by basename in the
    manifest's images map (so parsing stays offline)."""
    if img_el is None:
        return None
    base = _asset_basename(img_el.get("src") or "")
    meta = images.get(base)
    return meta["path"] if meta else None


def _parse_section(html: str, block: str, images: dict) -> list[dict]:
    """Walk one section page's content into raw question dicts:
    {num, stem, image, choices:[(text, image), …]}. Option `a` (the first <li>)
    is the published-correct answer."""
    root = _html.fromstring(html)
    try:
        content = root.get_element_by_id("content")
    except KeyError:
        content = root
    out: list[dict] = []
    cur: dict | None = None
    mode = "idle"          # idle -> (numbered <p>) -> "stem" -> (<ol>) -> idle
    for el in content.iter("p", "ol", "img"):
        if el.tag == "p":
            m = _NUM_STEM.match(_clean(el.text_content()))
            if m:
                cur = {"num": int(m.group(1)), "stem": _clean(m.group(2)),
                       "image": None, "choices": []}
                mode = "stem"
        elif el.tag == "img" and mode == "stem" and cur is not None:
            if cur["image"] is None and _is_figure(el.get("src") or ""):
                cur["image"] = _figure_path(el, images)
        elif el.tag == "ol" and mode == "stem" and cur is not None \
                and "elwisol" in (el.get("class") or "").lower():
            for li in el.findall("li"):
                cimg = _figure_path(li.find(".//img"), images)
                cur["choices"].append((_clean(li.text_content()), cimg))
            if len(cur["choices"]) >= 2:
                cur["block"] = block
                out.append(cur)
            cur, mode = None, "idle"
    return out


def parse(cat: Catalogue, manifest: dict) -> list[Question]:
    """Turn a catalogue's cached sections into verbatim `Question`s, themed and
    block-tagged, with deterministic option order and §5 attribution."""
    images = manifest.get("images", {})
    questions: list[Question] = []
    for sec in manifest["sections"]:
        path = os.path.join(_ROOT, sec["path"])
        with open(path, encoding="utf-8") as fh:
            html = fh.read()
        for raw in _parse_section(html, sec["block"], images):
            questions.append(_to_question(cat, sec["url"], raw))
    return questions


def _to_question(cat: Catalogue, section_url: str, raw: dict) -> Question:
    block = raw["block"]
    unit_id = f"elwis-{cat.id}-{cat.version}-q{raw['num']:03d}"
    qid = make_question_id(unit_id, raw["stem"])
    # Build choices verbatim; the published first option is the correct one.
    choices = [Choice(text=t, image=img, is_correct=(i == 0))
               for i, (t, img) in enumerate(raw["choices"])]
    # Permute the *display order* deterministically so "answer a" is not a tell.
    # The option text is unchanged — only its position — so the content stays
    # "unverändert" per the ELWIS terms.
    random.Random(_seed(qid)).shuffle(choices)

    haystack = raw["stem"] + " " + " ".join(t for t, _ in raw["choices"])
    theme = de_themes.tag_theme(text=haystack,
                                default=_DEFAULT_THEME_BY_BLOCK.get(block))
    return Question(
        id=qid, theme=theme, kind="official_mc", stem=raw["stem"], lang="de",
        image=raw["image"], choices=choices, block=block,
        provenance=Provenance(
            unit_id=unit_id, ref=f"Frage {raw['num']}",
            source=f"ELWIS Fragenkatalog {cat.label}, Stand 01.08.2023 "
                   f"(GDWS/WSV des Bundes)",
            url=section_url, as_of=cat.as_of, licence=LICENCE),
        explanation="", review_status="auto_approved",
        distractor_strategy="curated", generator=f"{GENERATOR}.{cat.id}.{cat.version}")


# --------------------------------------------------------------------------
# ingest: fetch + parse every catalogue, dedup the shared Basisfragen
# --------------------------------------------------------------------------

def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


def _dedup_key(q: Question):
    """A content key for a question, robust to the per-catalogue display shuffle.
    Keyed on stem + figure + the *set* of option texts (order-independent) — so a
    Basisfrage that See and Binnen genuinely share collapses, while two different
    figure questions that merely share a generic stem ("Was bedeutet dieses
    Tafelzeichen?") stay distinct (they differ in image and/or options).

    The figure is compared by basename, not path: See and Binnen each cache their
    own copy (…/see/… vs …/binnen/…) of the very same sign file, so a shared
    figure question must still collapse to one."""
    return (_norm(q.stem), os.path.basename(q.image or ""),
            frozenset(_norm(c.text) for c in q.choices))


def dedup_shared_basis(questions: list[Question]) -> tuple[list[Question], int]:
    """Drop duplicate Basisfragen — the 72 basic questions See and Binnen share —
    keeping the first occurrence of each (by content key). Only ``block ==
    "basis"`` questions are deduped; the catalogue-specific blocks are untouched.
    Returns (kept, n_dropped). Pure: no network, order-preserving."""
    out: list[Question] = []
    seen: set = set()
    dropped = 0
    for q in questions:
        if q.block == "basis":
            key = _dedup_key(q)
            if key in seen:
                dropped += 1
                continue
            seen.add(key)
        out.append(q)
    return out, dropped


def ingest(catalogue_ids: tuple[str, ...] = ("binnen", "see"),
           force: bool = False) -> tuple[list[Question], dict]:
    """Fetch + parse the requested catalogues into one verbatim German bank,
    deduping the Basisfragen 1–72 that See and Binnen share. Returns
    (questions, stats)."""
    parsed: list[Question] = []
    by_catalogue: dict[str, int] = {}
    for cid in catalogue_ids:
        cat = CATALOGUES[cid]
        qs = parse(cat, fetch(cat, force=force))
        by_catalogue[cid] = len(qs)
        parsed.extend(qs)

    out, dropped = dedup_shared_basis(parsed)
    stats = {"by_catalogue": by_catalogue, "by_block": {}, "by_theme": {},
             "with_image": 0, "basis_deduped": dropped, "total": len(out)}
    for q in out:
        stats["by_block"][q.block] = stats["by_block"].get(q.block, 0) + 1
        stats["by_theme"][q.theme] = stats["by_theme"].get(q.theme, 0) + 1
        if q.image:
            stats["with_image"] += 1
    return out, stats
