"""Stage 3 — merge all parsed units into one versioned SQLite knowledge base.

Responsibilities:
  * collect units from every source into the unified schema,
  * localize image assets (copy law images from the raw cache; download remote
    Wikipedia/Commons images) into data/assets/, so the KB is self-contained,
  * de-duplicate by id, link articles ↔ their annex figures,
  * stamp a KB version (the run date passed in) into the meta table,
  * also emit a single JSON export for portability / diffing.
"""

from __future__ import annotations

import os
import shutil
from collections import Counter

import requests

from . import schema
from .schema import KnowledgeUnit
from .sources import SOURCES
from .themes import THEMES

BASE = os.path.join(os.path.dirname(__file__), "..")
ASSET_DIR = os.path.join(BASE, "data", "assets")
RAW_DIR = os.path.join(BASE, "data", "raw")
HEADERS = {"User-Agent": "boat-permit-study/0.1 (Phase 1 aggregator; personal study tool)"}


def _localize_asset(path: str, source_id: str) -> str | None:
    """Ensure an asset lives under data/assets/ and return its repo-relative path.
    `path` is either already a data/assets/... path (law images) or a remote URL
    (Wikipedia). Returns None if it cannot be obtained."""
    if path.startswith("data/assets/"):
        dest = os.path.join(BASE, path)
        if os.path.exists(dest):
            return path
        # law image: copy from raw cache (data/raw/<src>/images/<file>)
        fname = os.path.basename(path)
        raw = os.path.join(RAW_DIR, source_id, "images", fname)
        if os.path.exists(raw):
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(raw, dest)
            return path
        return None
    if path.startswith("http"):
        fname = path.rsplit("/", 1)[-1].split("?")[0]
        rel = os.path.join("data", "assets", source_id, fname)
        dest = os.path.join(BASE, rel)
        if os.path.exists(dest):
            return rel
        try:
            r = requests.get(path, headers=HEADERS, timeout=60)
            r.raise_for_status()
        except requests.RequestException:
            return None
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as fh:
            fh.write(r.content)
        return rel
    return None


def normalize(parsed: dict[str, list[KnowledgeUnit]], db_path: str,
              version: str, json_path: str | None = None) -> dict:
    """Write all parsed units into the SQLite KB. Returns a stats dict."""
    units: list[KnowledgeUnit] = []
    seen_ids: set[str] = set()
    for src in SOURCES:
        for u in parsed.get(src.id, []):
            if u.id in seen_ids:
                continue
            seen_ids.add(u.id)
            kept = []
            for a in u.assets:
                local = _localize_asset(a.path, u.source_id)
                if local:
                    a.path = local
                    kept.append(a)
            u.assets = kept
            units.append(u)

    conn = schema.connect(db_path)
    # fresh build: clear prior rows so re-runs are clean
    conn.execute("DELETE FROM cross_refs")
    conn.execute("DELETE FROM assets")
    conn.execute("DELETE FROM units")
    conn.commit()
    schema.write_units(conn, units)
    schema.set_meta(conn, kb_version=version, unit_count=len(units),
                    source_count=len({u.source_id for u in units}))

    stats = {
        "units": len(units),
        "by_theme": dict(Counter(u.theme for u in units)),
        "by_kind": dict(Counter(u.kind for u in units)),
        "by_source": dict(Counter(u.source_id for u in units)),
        "assets": sum(len(u.assets) for u in units),
        "themes_missing": [t for t in THEMES if t not in {u.theme for u in units}],
    }

    if json_path:
        schema.export_json(conn, json_path)
    conn.close()
    return stats
