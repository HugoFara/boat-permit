"""Stage 1 — fetch raw sources to disk, verbatim, with provenance.

Each source caches under data/raw/<id>/ alongside a manifest.json recording the
exact URLs, retrieval date and (for law) the consolidated "état le" version.
Nothing re-fetches if the cache exists unless force=True, so stages stay cheap
and re-runnable. Fedlex is JS-rendered, so we never touch the page HTML: we
resolve structured files (Akoma Ntoso XML + PDF/A) via the SPARQL endpoint.
"""

from __future__ import annotations

import datetime as _dt
import io
import json
import os
import re
import time
import urllib.parse
import zipfile

import requests

from .sources import Source, SOURCES

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
SPARQL = "https://fedlex.data.admin.ch/sparqlendpoint"
GII_BASE = "https://www.gesetze-im-internet.de"
HEADERS = {"User-Agent": "boating-licence-study/0.1 (Phase 1 aggregator; personal study tool)"}
WP_API = "https://fr.wikipedia.org/w/api.php"


def _today() -> str:
    return _dt.date.today().isoformat()


def _raw_path(source_id: str, *parts: str) -> str:
    p = os.path.join(RAW_DIR, source_id, *parts)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p


def _get(url: str, **kw) -> requests.Response:
    """GET with polite retry/backoff on rate-limiting (429) and transient 5xx —
    Wikipedia in particular throttles bursts."""
    headers = {**HEADERS, **kw.pop("headers", {})}
    delay = 2.0
    for attempt in range(5):
        r = requests.get(url, headers=headers, timeout=60, **kw)
        if r.status_code in (429, 503) and attempt < 4:
            wait = float(r.headers.get("Retry-After", delay))
            time.sleep(wait)
            delay *= 2
            continue
        r.raise_for_status()
        return r
    r.raise_for_status()
    return r


# --------------------------------------------------------------------------
# Fedlex (law): resolve the newest XML (+ optional PDF/A) for an ELI, in any of
# the official languages. Swiss law is published officially in FR/DE/IT (and
# sometimes RM); each is a distinct `jolux:language` expression of the same act,
# so only the EU-authority language URI changes — the ELI is language-neutral.
# --------------------------------------------------------------------------

# EU Publications Office authority codes used by Fedlex's jolux:language.
_LANG_URI = {"fr": "FRA", "de": "DEU", "it": "ITA", "rm": "ROH"}

_FEDLEX_Q = """
PREFIX jolux: <http://data.legilux.public.lu/resource/ontology/jolux#>
SELECT ?file ?date WHERE {{
  ?expr jolux:isEmbodiedBy ?manif .
  ?manif jolux:isExemplifiedBy ?file .
  ?expr jolux:language <http://publications.europa.eu/resource/authority/language/{languri}> .
  ?cons jolux:isRealizedBy ?expr .
  ?cons jolux:dateApplicability ?date .
  FILTER(CONTAINS(STR(?file), "{eli}"))
  FILTER(CONTAINS(STR(?file), "/{fmt}/"))
}}
ORDER BY DESC(?date) LIMIT 1
"""


def _resolve_fedlex_file(eli: str, fmt: str, lang: str = "fr") -> tuple[str, str] | None:
    """Return (file_url, consolidation_date) for the newest `lang` `fmt` manifestation."""
    q = _FEDLEX_Q.format(eli=eli, fmt=fmt, languri=_LANG_URI[lang])
    r = _get(SPARQL, params={"query": q},
             headers={**HEADERS, "Accept": "application/sparql-results+json"})
    rows = r.json()["results"]["bindings"]
    if not rows:
        return None
    b = rows[0]
    return b["file"]["value"], b["date"]["value"]


def _fetch_xml_images(cache_key: str, xml_url: str, xml_bytes: bytes) -> dict:
    """Download every distinct image referenced by the act XML. Returns
    {src_ref: {"path": local, "bytes": n}} keyed by the ref used in the XML."""
    from lxml import etree
    AKN = "{http://docs.oasis-open.org/legaldocml/ns/akn/3.0}"
    root = etree.fromstring(xml_bytes)
    base = xml_url.rsplit("/", 1)[0]
    refs = sorted({im.get("src") for im in root.iter(AKN + "img") if im.get("src")})
    out = {}
    for ref in refs:
        url = urllib.parse.urljoin(base + "/", ref)
        try:
            content = _get(url).content
        except requests.HTTPError:
            continue
        local = _raw_path(cache_key, "images", os.path.basename(ref))
        with open(local, "wb") as fh:
            fh.write(content)
        out[ref] = {"path": os.path.relpath(local), "bytes": len(content), "url": url}
    return out


def fetch_fedlex(src: Source, force: bool = False, lang: str = "fr") -> dict:
    """Fetch one act in one language. French keeps the legacy cache layout
    (data/raw/<id>/); other languages live in a per-language subdir
    (data/raw/<id>/<lang>/) so the FR build is untouched."""
    if lang not in _LANG_URI:
        raise ValueError(f"unsupported fedlex language {lang!r}")
    cache_key = src.id if lang == "fr" else os.path.join(src.id, lang)
    manifest_path = _raw_path(cache_key, "manifest.json")
    if os.path.exists(manifest_path) and not force:
        with open(manifest_path, encoding="utf-8") as fh:
            return json.load(fh)

    files: dict[str, str] = {}
    version = ""
    xml = _resolve_fedlex_file(src.eli, "xml", lang)
    if not xml:
        raise RuntimeError(
            f"[{src.id}] no Fedlex {lang.upper()} XML found for ELI {src.eli}")
    xml_url, version = xml
    xml_bytes = _get(xml_url).content
    xml_local = _raw_path(cache_key, "act.xml")
    with open(xml_local, "wb") as fh:
        fh.write(xml_bytes)
    files["xml"] = {"url": xml_url, "path": os.path.relpath(xml_local)}

    # Annex figures: the XML references images relatively ("image/imageN.png").
    # They resolve from the same filestore directory as the XML — pull them so
    # the signalisation theme has its diagrams, named and in article context.
    images = _fetch_xml_images(cache_key, xml_url, xml_bytes)
    if images:
        files["images"] = images

    if src.want_pdf:
        pdf = _resolve_fedlex_file(src.eli, "pdf-a", lang)
        if pdf:
            pdf_url, _ = pdf
            pdf_local = _raw_path(cache_key, "act.pdf")
            with open(pdf_local, "wb") as fh:
                fh.write(_get(pdf_url).content)
            files["pdf"] = {"url": pdf_url, "path": os.path.relpath(pdf_local)}

    manifest = {
        "source_id": src.id, "kind": src.kind, "lang": lang, "retrieved": _today(),
        "legal_version": version, "files": files, "canonical_url": src.url,
    }
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    return manifest


# --------------------------------------------------------------------------
# gesetze-im-internet.de (German federal law): each ordinance ships as a single
# <slug>/xml.zip — one gii-norm XML plus any bundled annex images. Public domain
# under §5(1) UrhG. The German analogue of the Fedlex path; German law is
# single-language, so there is no per-language manifestation to resolve.
# --------------------------------------------------------------------------

def _gii_version(xml_path: str) -> str:
    """Best-effort 'as-of' for a gii act: the 'Stand' comment if present, else the
    promulgation (Ausfertigung) date — read from the framing header norm."""
    from lxml import etree
    root = etree.parse(xml_path).getroot()
    stand = root.findtext(".//standangabe/standkommentar")
    if stand and stand.strip():
        return re.sub(r"\s+", " ", stand).strip()
    aus = root.findtext(".//ausfertigung-datum")
    return (aus or "").strip()


def fetch_gii(src: Source, force: bool = False, lang: str = "de") -> dict:
    """Fetch one German ordinance. Mirrors fetch_fedlex's cache layout: FR (n/a
    here) would stay flat, other languages live under data/raw/<id>/<lang>/."""
    cache_key = src.id if lang == "fr" else os.path.join(src.id, lang)
    manifest_path = _raw_path(cache_key, "manifest.json")
    if os.path.exists(manifest_path) and not force:
        with open(manifest_path, encoding="utf-8") as fh:
            return json.load(fh)

    slug = src.gii_slug or src.id
    url = f"{GII_BASE}/{slug}/xml.zip"
    zf = zipfile.ZipFile(io.BytesIO(_get(url).content))

    files: dict = {}
    images: dict = {}
    xml_local = ""
    for name in zf.namelist():
        if name.endswith("/"):
            continue
        data = zf.read(name)
        base = os.path.basename(name)
        if base.lower().endswith(".xml"):
            xml_local = _raw_path(cache_key, "act.xml")
            with open(xml_local, "wb") as fh:
                fh.write(data)
            files["xml"] = {"url": url, "path": os.path.relpath(xml_local)}
        else:                                  # bundled annex image, keyed by name
            local = _raw_path(cache_key, "images", base)
            with open(local, "wb") as fh:
                fh.write(data)
            images[base] = {"path": os.path.relpath(local), "bytes": len(data)}
    if not xml_local:
        raise RuntimeError(f"[{src.id}] no XML found in {url}")
    if images:
        files["images"] = images

    manifest = {
        "source_id": src.id, "kind": src.kind, "lang": lang, "retrieved": _today(),
        "legal_version": _gii_version(xml_local), "files": files,
        "canonical_url": src.url,
    }
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    return manifest


# --------------------------------------------------------------------------
# Wikipedia: pull parsed HTML + revision id per page via the MediaWiki API.
# --------------------------------------------------------------------------

def fetch_wikipedia(src: Source, force: bool = False) -> dict:
    manifest_path = _raw_path(src.id, "manifest.json")
    if os.path.exists(manifest_path) and not force:
        with open(manifest_path, encoding="utf-8") as fh:
            return json.load(fh)

    api = f"https://{src.lang}.wikipedia.org/w/api.php"   # language edition
    pages = {}
    for i, title in enumerate(src.titles):
        if i:
            time.sleep(1.0)            # be polite: one page/sec
        r = _get(api, params={
            "action": "parse", "page": title, "prop": "text|revid",
            "format": "json", "redirects": 1, "formatversion": 2,
        })
        data = r.json()
        if "error" in data:
            pages[title] = {"error": data["error"].get("info", "unknown")}
            continue
        p = data["parse"]
        local = _raw_path(src.id, f"page_{p.get('revid', 0)}.html")
        with open(local, "w", encoding="utf-8") as fh:
            fh.write(p["text"])
        pages[title] = {"revid": p.get("revid"), "path": os.path.relpath(local),
                        "real_title": p.get("title", title)}

    manifest = {
        "source_id": src.id, "kind": src.kind, "lang": src.lang,
        "retrieved": _today(),
        "legal_version": "", "pages": pages, "canonical_url": src.url,
    }
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    return manifest


# --------------------------------------------------------------------------
# Generic HTML: cache the raw page verbatim.
# --------------------------------------------------------------------------

def fetch_html(src: Source, force: bool = False) -> dict:
    manifest_path = _raw_path(src.id, "manifest.json")
    if os.path.exists(manifest_path) and not force:
        with open(manifest_path, encoding="utf-8") as fh:
            return json.load(fh)

    r = _get(src.url)
    local = _raw_path(src.id, "page.html")
    with open(local, "wb") as fh:
        fh.write(r.content)
    manifest = {
        "source_id": src.id, "kind": src.kind, "retrieved": _today(),
        "legal_version": r.headers.get("Last-Modified", ""),
        "files": {"html": {"url": src.url, "path": os.path.relpath(local)}},
        "canonical_url": src.url,
        "final_url": r.url,
    }
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    return manifest


def fetch_pdf(src: Source, force: bool = False) -> dict:
    """Cache a PDF document verbatim (e.g. the USCG COLREG International Rules).
    Single-language, like the HTML/Wikipedia sources — the file is fetched only
    when the source's own `lang` is requested; its text is segmented at parse time
    (no per-language manifestation to resolve)."""
    manifest_path = _raw_path(src.id, "manifest.json")
    if os.path.exists(manifest_path) and not force:
        with open(manifest_path, encoding="utf-8") as fh:
            return json.load(fh)

    r = _get(src.url)
    local = _raw_path(src.id, "doc.pdf")
    with open(local, "wb") as fh:
        fh.write(r.content)
    manifest = {
        "source_id": src.id, "kind": src.kind, "lang": src.lang,
        "retrieved": _today(),
        "legal_version": r.headers.get("Last-Modified", ""),
        "files": {"pdf": {"url": src.url, "path": os.path.relpath(local),
                          "bytes": len(r.content)}},
        "canonical_url": src.url,
        "final_url": r.url,
    }
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    return manifest


_DISPATCH = {"fedlex": fetch_fedlex, "gii": fetch_gii,
             "wikipedia": fetch_wikipedia, "html": fetch_html, "pdf": fetch_pdf}
# Law sources fetched as a per-language manifestation of one act.
_PER_LANG_KINDS = {"fedlex", "gii"}


def fetch_source(src: Source, force: bool = False) -> dict:
    return _DISPATCH[src.kind](src, force=force)


def fetch_all(sources: list[Source] | None = None, force: bool = False) -> dict[str, dict]:
    out = {}
    for src in (sources or SOURCES):
        out[src.id] = fetch_source(src, force=force)
    return out


def fetch_fedlex_langs(langs: list[str], sources: list[Source] | None = None,
                       force: bool = False) -> dict[str, dict]:
    """Fetch the law (fedlex) sources in additional official languages (de/it).
    Keyed '<id>/<lang>'."""
    out = {}
    for src in (sources or SOURCES):
        if src.kind != "fedlex":
            continue
        for lang in langs:
            out[f"{src.id}/{lang}"] = fetch_fedlex(src, force=force, lang=lang)
    return out


def fetch_for_langs(langs: list[str], sources: list[Source] | None = None,
                    force: bool = False) -> dict[str, dict]:
    """Fetch every source needed for the requested content languages. Law
    (fedlex) acts are fetched once per language (same act, different manifestation);
    language-specific sources (Wikipedia/HTML) are fetched only when their own
    `lang` is requested. Keyed '<id>' (fr law / lang-specific source) or
    '<id>/<lang>' (non-fr law)."""
    out = {}
    for src in (sources or SOURCES):
        if src.kind in _PER_LANG_KINDS:
            for lang in langs:
                key = src.id if lang == "fr" else f"{src.id}/{lang}"
                out[key] = _DISPATCH[src.kind](src, force=force, lang=lang)
        elif src.lang in langs:
            out[src.id] = fetch_source(src, force=force)
    return out
