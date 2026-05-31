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
from .themes import THEMES, EXTENSION_THEMES

BASE = os.path.join(os.path.dirname(__file__), "..")
ASSET_DIR = os.path.join(BASE, "data", "assets")
RAW_DIR = os.path.join(BASE, "data", "raw")
HEADERS = {"User-Agent": "boating-licence-study/0.1 (Phase 1 aggregator; personal study tool)"}


def _localize_asset(path: str, source_id: str, lang: str = "fr") -> str | None:
    """Ensure an asset lives under data/assets/ and return its repo-relative path.
    `path` is either already a data/assets/... path (law images) or a remote URL
    (Wikipedia). Returns None if it cannot be obtained."""
    if path.startswith("data/assets/"):
        dest = os.path.join(BASE, path)
        if os.path.exists(dest):
            return path
        # law image: copy from the raw cache (data/raw/<src>[/<lang>]/images/<file>)
        fname = os.path.basename(path)
        raw_sub = source_id if lang == "fr" else os.path.join(source_id, lang)
        raw = os.path.join(RAW_DIR, raw_sub, "images", fname)
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


def _propagate_themes(units: list[KnowledgeUnit], base_lang: str = "fr") -> int:
    """Cross-language theme propagation for articles. The Swiss `themes.tag_theme`
    keys on French wording, so a German/Italian article keyword-tags poorly and
    falls to its source default. But the same article is parallel across languages
    under a language-neutral ref ("ONI art. 23" is identical in fr/de/it), so each
    non-base-language article inherits its base sibling's (correctly-tagged) theme.
    Returns the count of units whose theme was corrected. No-op when the base
    language isn't in the build (e.g. a single-language German build), and figures
    keep their language-independent default ('signalisation'). Idempotent."""
    base_theme = {u.ref: u.theme for u in units
                  if u.lang == base_lang and u.kind == "article"}
    changed = 0
    for u in units:
        if u.lang != base_lang and u.kind == "article":
            target = base_theme.get(u.ref)
            if target is not None and target != u.theme:
                u.theme = target
                changed += 1
    return changed


def normalize(parsed: dict[str, list[KnowledgeUnit]], db_path: str,
              version: str, json_path: str | None = None,
              themes_table: dict | None = None,
              extension_themes: frozenset | None = None,
              base_lang: str = "fr", country_code: str = "INT") -> dict:
    """Write all parsed units into the SQLite KB. Returns a stats dict. The theme
    table / extension set / base language default to the Swiss ones, so the
    original CH build is unchanged; pass a country's values for other builds."""
    themes_table = THEMES if themes_table is None else themes_table
    extension_themes = (EXTENSION_THEMES if extension_themes is None
                        else extension_themes)
    units: list[KnowledgeUnit] = []
    seen_ids: set[str] = set()
    # Iterate parsed values in insertion order (FR first, then any DE/IT) so the
    # KB ordering is stable; ids are lang-unique so parallel acts coexist.
    for batch in parsed.values():
        for u in batch:
            if u.id in seen_ids:
                continue
            seen_ids.add(u.id)
            kept = []
            for a in u.assets:
                local = _localize_asset(a.path, u.source_id, u.lang)
                if local:
                    a.path = local
                    kept.append(a)
            u.assets = kept
            units.append(u)

    propagated = _propagate_themes(units, base_lang)

    conn = schema.connect(db_path)
    # fresh build: clear prior rows so re-runs are clean
    conn.execute("DELETE FROM cross_refs")
    conn.execute("DELETE FROM assets")
    conn.execute("DELETE FROM units")
    conn.commit()
    schema.write_units(conn, units)
    schema.set_meta(conn, kb_version=version, country=country_code,
                    unit_count=len(units),
                    source_count=len({u.source_id for u in units}),
                    languages=",".join(sorted({u.lang for u in units})))

    stats = {
        "units": len(units),
        "by_theme": dict(Counter(u.theme for u in units)),
        "by_kind": dict(Counter(u.kind for u in units)),
        "by_source": dict(Counter(u.source_id for u in units)),
        "by_lang": dict(Counter(u.lang for u in units)),
        "assets": sum(len(u.assets) for u in units),
        "themes_propagated": propagated,
        # Extension themes (e.g. cat-D `voile`, or German catalogue-only topics)
        # are scaffolded ahead of a source, so a law-only build legitimately has
        # no units for them — don't warn.
        "themes_missing": [t for t in themes_table
                           if t not in {u.theme for u in units}
                           and t not in extension_themes],
    }

    if json_path:
        schema.export_json(conn, json_path)
    conn.close()
    return stats
