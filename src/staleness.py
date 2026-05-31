"""Stage 0.5 — staleness: has any upstream source drifted from the blessed version?

Every committed knowledge base was derived from a *specific* version of each
upstream law / question catalogue, but nothing recorded *which* one — so an
amendment upstream only ever surfaced when a human happened to notice. This module
pins a committed ``data/sources.lock.json`` of blessed fingerprints and diffs the
current upstream against it, so a scheduled job (see
``.github/workflows/staleness.yml``) flags drift the moment it lands instead of
months later.

A *fingerprint* is ``{legal_version, digest}`` — the source's own version marker
(fedlex "état le" consolidation date / gii "Stand" / ELWIS catalogue "Stand" /
the LEGI per-article DATE_DEBUT set) plus a sha256 of the fetched bytes. Either
moving means the source moved; the digest catches editorial changes a version
string wouldn't bump.

Every source is fingerprinted the *same* way — a hash of its cached raw bytes
under ``data/raw/<id>/``. ``--update``/``check(force=True)`` refreshes that cache
from upstream first (the network step); without it the check hashes whatever is on
disk (offline / CI-cache mode). Blessing and checking therefore hash an identical
file set and stay comparable.

Drift is *graded*: law-grade sources (``fedlex``/``gii``/``pdf``/ELWIS/LEGI) are
**significant** — a derived question may now be wrong, so the check exits non-zero.
Reference sources (Wikipedia/HTML prose) are **advisory** — reported, never fatal.

    python run.py check-sources            # re-fetch upstream, diff against the lock
    python run.py check-sources --offline  # hash the on-disk cache only (no network)
    python run.py check-sources --update   # re-fetch, then bless the current state

Limitation, stated plainly (no silent caps): the FR **LEGI** fingerprint pins the
*committed* ``src/fr/legi_kb.json`` corpus, not Légifrance live — true upstream FR
drift is only caught after a fresh ``python -m src.fr.legi extract`` re-ingests the
DILA dump. The check logs this so the gap is never mistaken for "FR is current".
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os

from . import fetch
from .countries import registry

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(ROOT, "data", "raw")
LOCK_PATH = os.path.join(ROOT, "data", "sources.lock.json")
LEGI_KB = os.path.join(ROOT, "src", "fr", "legi_kb.json")

# Kinds whose drift can invalidate a derived question (vs reference prose). ELWIS
# and LEGI are law-grade too; they're fingerprinted by dedicated helpers below.
_LAW_KINDS = {"fedlex", "gii", "pdf"}


def _grade(kind: str) -> str:
    return "law" if kind in _LAW_KINDS else "reference"


# --------------------------------------------------------------------------
# Digesting cached raw bytes
# --------------------------------------------------------------------------

def _content_files(rel_dir: str) -> list[str]:
    """Every cached content file under ``data/raw/<rel_dir>/``, sorted — excluding
    each ``manifest.json`` (its version is captured separately) and any ``images/``
    subtree (annex figures rarely change and would only add noise)."""
    base = os.path.join(RAW_DIR, rel_dir)
    out: list[str] = []
    for dirpath, _dirs, filenames in os.walk(base):
        rel_parts = set(os.path.relpath(dirpath, base).split(os.sep))
        if "images" in rel_parts:
            continue
        for fn in filenames:
            if fn == "manifest.json":
                continue
            out.append(os.path.join(dirpath, fn))
    return sorted(out)


def _digest(paths: list[str]) -> str:
    """A short sha256 over the named files' bytes (name included, so a rename or a
    dropped file shows as drift too). Empty when nothing is cached."""
    if not paths:
        return ""
    h = hashlib.sha256()
    for p in paths:
        h.update(os.path.relpath(p, RAW_DIR).encode())
        with open(p, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
    return h.hexdigest()[:16]


def _manifest_version(source_id: str) -> str:
    """The source's own version marker. A `fr`-default act caches its manifest at
    ``data/raw/<id>/manifest.json``; a single-language act (the German gii/fedlex
    sources are fetched only in `de`) caches it one level down at
    ``…/<id>/<lang>/manifest.json`` — so fall back to the first lang subdir."""
    candidates = [os.path.join(RAW_DIR, source_id, "manifest.json")]
    sub = os.path.join(RAW_DIR, source_id)
    if os.path.isdir(sub):
        candidates += sorted(os.path.join(sub, d, "manifest.json")
                             for d in os.listdir(sub)
                             if os.path.isdir(os.path.join(sub, d)))
    for mp in candidates:
        if os.path.exists(mp):
            with open(mp, encoding="utf-8") as fh:
                v = json.load(fh).get("legal_version", "")
            if v:
                return v
    return ""


# --------------------------------------------------------------------------
# Per-source fingerprints
# --------------------------------------------------------------------------

def _fp_fetch_source(src, refresh: bool) -> dict:
    """Fingerprint a `fetch.py`-tracked source (fedlex/gii/wikipedia/html/pdf)."""
    if refresh:
        fetch.fetch_source(src, force=True)
    return {"kind": src.kind, "grade": _grade(src.kind),
            "legal_version": _manifest_version(src.id),
            "digest": _digest(_content_files(src.id))}


def _fp_elwis(refresh: bool) -> dict:
    """Fingerprint the official ELWIS Fragenkataloge — Germany's amtliche catalogue
    and the one bank under live reform, so the highest-value drift signal here. The
    `version` is hardcoded per :data:`elwis.CATALOGUES`, so a reform that keeps the
    page URL but changes the questions would slip past a version check — the byte
    digest is what catches it."""
    from .questions import elwis
    if refresh:
        for cat in elwis.CATALOGUES.values():
            elwis.fetch(cat, force=True)
    files: list[str] = []
    versions: list[str] = []
    for cid, cat in sorted(elwis.CATALOGUES.items()):
        files += _content_files(os.path.join("elwis", cat.id, cat.version))
        versions.append(f"{cid}:{cat.version}")
    return {"kind": "elwis", "grade": "law",
            "legal_version": ";".join(versions), "digest": _digest(files)}


def _fp_path_country(country) -> dict:
    """Fingerprint one country's committed path-to-permit facts (age/medical/
    practical/application/fees/validity). Like :func:`_fp_legi`, this pins the
    *committed* authored data, not live upstream — the official pages aren't polled,
    so a drift only shows when the facts are edited (the prompt to re-bless). The
    oldest ``as_of`` is surfaced in ``legal_version`` so aging facts get re-verified.
    Graded ``reference`` (advisory): stale procedural info should be reported, but it
    doesn't invalidate a derived question the way a law change does."""
    h = hashlib.sha256()
    as_ofs: list[str] = []
    steps = country.path_manifest()
    for s in steps:
        as_ofs.append(s.get("as_of", ""))
        h.update(("|".join((s["code"], s["region_scope"],
                            ",".join(s["permit_scope"]), s["url"],
                            s["as_of"], "1" if s["volatile"] else "0"))).encode())
        for lg in sorted(s["body"]):
            h.update(f"{lg}={s['body'][lg]}".encode())
    oldest = min((a for a in as_ofs if a), default="")
    return {"kind": "path", "grade": "reference",
            "legal_version": f"{len(steps)} steps, oldest as_of {oldest}",
            "digest": h.hexdigest()[:16]}


def _fp_legi() -> dict:
    """Fingerprint the committed FR LEGI corpus by its per-article DATE_DEBUT set.
    This is a tripwire for a re-extract that changes article versions; it does *not*
    poll Légifrance live (that needs a fresh DILA dump — see the module docstring)."""
    with open(LEGI_KB, encoding="utf-8") as fh:
        kb = json.load(fh)
    units = kb.get("units", [])
    h = hashlib.sha256()
    for u in sorted(units, key=lambda x: x.get("id", "")):
        h.update(f"{u.get('id','')}|{u.get('legal_version','')}".encode())
    return {"kind": "legi", "grade": "law",
            "legal_version": f"{kb.get('meta', {}).get('kb_version', '')} "
                             f"({len(units)} units, corpus-pinned)",
            "digest": h.hexdigest()[:16]}


# --------------------------------------------------------------------------
# Snapshot / lock / diff
# --------------------------------------------------------------------------

def _all_sources() -> dict:
    """Every distinct `fetch.py` Source across all countries, keyed by id (dedup:
    the BSO fedlex act, for instance, is shared by CH and DE)."""
    out = {}
    for country in registry.COUNTRIES.values():
        for src in country.sources:
            out.setdefault(src.id, src)
    return out


def snapshot(refresh: bool = True) -> dict:
    """Fingerprint every source now. ``refresh`` re-fetches upstream first."""
    fps: dict[str, dict] = {}
    for sid, src in sorted(_all_sources().items()):
        fps[sid] = _fp_fetch_source(src, refresh)
    fps["elwis"] = _fp_elwis(refresh)
    fps["legi"] = _fp_legi()
    # Path-to-permit facts, one fingerprint per country that ships them.
    for code in sorted(registry.COUNTRIES):
        country = registry.COUNTRIES[code]
        if country.path:
            fps[f"path:{code}"] = _fp_path_country(country)
    return fps


def load_lock() -> dict:
    if not os.path.exists(LOCK_PATH):
        return {}
    with open(LOCK_PATH, encoding="utf-8") as fh:
        return json.load(fh).get("sources", {})


def write_lock(fps: dict) -> None:
    payload = {"blessed": _dt.date.today().isoformat(),
               "note": "Blessed upstream versions; `python run.py check-sources` "
                       "diffs live upstream against this. Update with --update after "
                       "re-deriving the affected bank.",
               "sources": dict(sorted(fps.items()))}
    with open(LOCK_PATH, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def diff(lock: dict, current: dict) -> list[dict]:
    """Per-source change records: status added|removed|changed, with the grade and
    the old→new version/digest. Unchanged sources are omitted."""
    changes: list[dict] = []
    for sid in sorted(set(lock) | set(current)):
        was, now = lock.get(sid), current.get(sid)
        if was and not now:
            changes.append({"id": sid, "status": "removed",
                            "grade": was.get("grade", "law")})
        elif now and not was:
            changes.append({"id": sid, "status": "added", "grade": now["grade"]})
        elif was != now:
            moved = (was.get("legal_version") != now.get("legal_version"),
                     was.get("digest") != now.get("digest"))
            changes.append({
                "id": sid, "status": "changed", "grade": now["grade"],
                "version": (was.get("legal_version"), now.get("legal_version")),
                "digest": (was.get("digest"), now.get("digest")),
                "what": ", ".join(w for w, f in
                                  zip(("version", "content"), moved) if f)})
    return changes


# --------------------------------------------------------------------------
# Top-level check (the CLI / CI entrypoint)
# --------------------------------------------------------------------------

def check(refresh: bool = True, update: bool = False) -> tuple[list[dict], bool]:
    """Compare live upstream against the lock. Returns (changes, significant) where
    `significant` is True iff a *law*-grade source drifted (CI should fail). With
    ``update=True``, rewrites the lock to the current snapshot (blessing the state)."""
    current = snapshot(refresh=refresh)
    changes = diff(load_lock(), current)
    if update:
        write_lock(current)
    significant = any(c["grade"] == "law" for c in changes)
    return changes, significant


def format_report(changes: list[dict]) -> str:
    if not changes:
        return "✓ All sources match the blessed lock — no upstream drift."
    lines = ["Upstream drift vs data/sources.lock.json:", ""]
    for c in changes:
        mark = "‼" if c["grade"] == "law" else "·"
        if c["status"] == "changed":
            lines.append(f"  {mark} {c['id']:14} {c['grade']:9} changed "
                         f"({c['what']})")
            if c.get("version") and c["version"][0] != c["version"][1]:
                lines.append(f"      version: {c['version'][0]!r} → "
                             f"{c['version'][1]!r}")
        else:
            lines.append(f"  {mark} {c['id']:14} {c['grade']:9} {c['status']}")
    law = [c for c in changes if c["grade"] == "law"]
    lines += ["", f"{len(law)} law-grade change(s) — re-derive the affected bank, "
                  f"then `python run.py check-sources --update` to re-bless."]
    return "\n".join(lines)
