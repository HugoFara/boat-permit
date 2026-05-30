"""Stage 1 — fetch raw sources to disk, verbatim, with provenance.

Each source caches under data/raw/<id>/ alongside a manifest.json recording the
exact URLs, retrieval date and (for law) the consolidated "état le" version.
Nothing re-fetches if the cache exists unless force=True, so stages stay cheap
and re-runnable. Fedlex is JS-rendered, so we never touch the page HTML: we
resolve structured files (Akoma Ntoso XML + PDF/A) via the SPARQL endpoint.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import urllib.parse

import requests

from .sources import Source, SOURCES

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
SPARQL = "https://fedlex.data.admin.ch/sparqlendpoint"
HEADERS = {"User-Agent": "boat-permit-study/0.1 (Phase 1 aggregator; personal study tool)"}
WP_API = "https://fr.wikipedia.org/w/api.php"


def _today() -> str:
    return _dt.date.today().isoformat()


def _raw_path(source_id: str, *parts: str) -> str:
    p = os.path.join(RAW_DIR, source_id, *parts)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p


def _get(url: str, **kw) -> requests.Response:
    headers = {**HEADERS, **kw.pop("headers", {})}
    r = requests.get(url, headers=headers, timeout=60, **kw)
    r.raise_for_status()
    return r


# --------------------------------------------------------------------------
# Fedlex (law): resolve newest French XML (+ optional PDF/A) for an ELI.
# --------------------------------------------------------------------------

_FEDLEX_Q = """
PREFIX jolux: <http://data.legilux.public.lu/resource/ontology/jolux#>
SELECT ?file ?date WHERE {{
  ?expr jolux:isEmbodiedBy ?manif .
  ?manif jolux:isExemplifiedBy ?file .
  ?expr jolux:language <http://publications.europa.eu/resource/authority/language/FRA> .
  ?cons jolux:isRealizedBy ?expr .
  ?cons jolux:dateApplicability ?date .
  FILTER(CONTAINS(STR(?file), "{eli}"))
  FILTER(CONTAINS(STR(?file), "/{fmt}/"))
}}
ORDER BY DESC(?date) LIMIT 1
"""


def _resolve_fedlex_file(eli: str, fmt: str) -> tuple[str, str] | None:
    """Return (file_url, consolidation_date) for the newest FR `fmt` manifestation."""
    q = _FEDLEX_Q.format(eli=eli, fmt=fmt)
    r = _get(SPARQL, params={"query": q},
             headers={**HEADERS, "Accept": "application/sparql-results+json"})
    rows = r.json()["results"]["bindings"]
    if not rows:
        return None
    b = rows[0]
    return b["file"]["value"], b["date"]["value"]


def _fetch_xml_images(source_id: str, xml_url: str, xml_bytes: bytes) -> dict:
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
        local = _raw_path(source_id, "images", os.path.basename(ref))
        with open(local, "wb") as fh:
            fh.write(content)
        out[ref] = {"path": os.path.relpath(local), "bytes": len(content), "url": url}
    return out


def fetch_fedlex(src: Source, force: bool = False) -> dict:
    manifest_path = _raw_path(src.id, "manifest.json")
    if os.path.exists(manifest_path) and not force:
        with open(manifest_path, encoding="utf-8") as fh:
            return json.load(fh)

    files: dict[str, str] = {}
    version = ""
    xml = _resolve_fedlex_file(src.eli, "xml")
    if not xml:
        raise RuntimeError(f"[{src.id}] no Fedlex FR XML found for ELI {src.eli}")
    xml_url, version = xml
    xml_bytes = _get(xml_url).content
    xml_local = _raw_path(src.id, "act.xml")
    with open(xml_local, "wb") as fh:
        fh.write(xml_bytes)
    files["xml"] = {"url": xml_url, "path": os.path.relpath(xml_local)}

    # Annex figures: the XML references images relatively ("image/imageN.png").
    # They resolve from the same filestore directory as the XML — pull them so
    # the signalisation theme has its diagrams, named and in article context.
    images = _fetch_xml_images(src.id, xml_url, xml_bytes)
    if images:
        files["images"] = images

    if src.want_pdf:
        pdf = _resolve_fedlex_file(src.eli, "pdf-a")
        if pdf:
            pdf_url, _ = pdf
            pdf_local = _raw_path(src.id, "act.pdf")
            with open(pdf_local, "wb") as fh:
                fh.write(_get(pdf_url).content)
            files["pdf"] = {"url": pdf_url, "path": os.path.relpath(pdf_local)}

    manifest = {
        "source_id": src.id, "kind": src.kind, "retrieved": _today(),
        "legal_version": version, "files": files, "canonical_url": src.url,
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

    pages = {}
    for title in src.titles:
        r = _get(WP_API, params={
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
        "source_id": src.id, "kind": src.kind, "retrieved": _today(),
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


_DISPATCH = {"fedlex": fetch_fedlex, "wikipedia": fetch_wikipedia, "html": fetch_html}


def fetch_source(src: Source, force: bool = False) -> dict:
    return _DISPATCH[src.kind](src, force=force)


def fetch_all(sources: list[Source] | None = None, force: bool = False) -> dict[str, dict]:
    out = {}
    for src in (sources or SOURCES):
        out[src.id] = fetch_source(src, force=force)
    return out
