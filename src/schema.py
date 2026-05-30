"""Knowledge-unit schema + SQLite persistence.

One normalized record type for everything (article, annex figure, prose
section). Assets and cross-refs live in child tables. The KB is versioned by a
single `meta` row so re-runs are reproducible and Phase 2 can pin a version.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field, asdict


@dataclass
class Asset:
    type: str            # "image"
    path: str            # repo-relative path under data/assets/
    caption: str = ""


@dataclass
class KnowledgeUnit:
    id: str                      # stable, derived from source + ref (+ lang)
    theme: str                   # theme id from themes.THEMES
    kind: str                    # "article" | "annex_figure" | "prose_section"
    ref: str                     # e.g. "ONI art. 23" / "ONI annexe 4, fig. 12"
    title: str
    text: str
    # provenance
    source_id: str
    source_name: str
    source_url: str
    retrieved: str               # ISO date
    legal_version: str           # "état le" date or page version, "" if n/a
    licence: str
    lang: str = "fr"             # content language (fr/de/it); fr is canonical
    assets: list[Asset] = field(default_factory=list)
    cross_refs: list[str] = field(default_factory=list)


def make_id(source_id: str, ref: str, lang: str = "fr") -> str:
    """Stable id: human-readable prefix + short hash of the full ref so re-runs
    produce identical ids (no random/auto-increment). French keeps the legacy
    id (no lang segment) so existing FR units/questions are byte-stable; other
    languages get a distinct prefix + hash so the parallel acts don't collide."""
    slug = ref.lower().replace(" ", "_").replace(".", "").replace(",", "")
    slug = "".join(c for c in slug if c.isalnum() or c == "_")[:48]
    key = source_id if lang == "fr" else f"{source_id}@{lang}"
    prefix = source_id if lang == "fr" else f"{source_id}-{lang}"
    digest = hashlib.sha1(f"{key}:{ref}".encode()).hexdigest()[:8]
    return f"{prefix}-{slug}-{digest}"


DDL = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
CREATE TABLE IF NOT EXISTS units (
    id            TEXT PRIMARY KEY,
    theme         TEXT NOT NULL,
    kind          TEXT NOT NULL,
    ref           TEXT NOT NULL,
    title         TEXT,
    text          TEXT,
    source_id     TEXT NOT NULL,
    source_name   TEXT,
    source_url    TEXT,
    retrieved     TEXT,
    legal_version TEXT,
    licence       TEXT,
    lang          TEXT NOT NULL DEFAULT 'fr'
);
CREATE TABLE IF NOT EXISTS assets (
    unit_id TEXT NOT NULL REFERENCES units(id) ON DELETE CASCADE,
    type    TEXT NOT NULL,
    path    TEXT NOT NULL,
    caption TEXT
);
CREATE TABLE IF NOT EXISTS cross_refs (
    unit_id TEXT NOT NULL REFERENCES units(id) ON DELETE CASCADE,
    ref_id  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_units_theme  ON units(theme);
CREATE INDEX IF NOT EXISTS idx_units_source ON units(source_id);
CREATE INDEX IF NOT EXISTS idx_assets_unit  ON assets(unit_id);
"""


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(DDL)
    _migrate(conn)
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    """Idempotent, additive migration for KBs created before the lang column."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(units)")}
    if "lang" not in cols:
        conn.execute("ALTER TABLE units ADD COLUMN lang TEXT NOT NULL DEFAULT 'fr'")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_units_lang ON units(lang)")
    conn.commit()


def write_units(conn: sqlite3.Connection, units: list[KnowledgeUnit]) -> None:
    """Idempotent upsert of a batch of units (replaces by id)."""
    cur = conn.cursor()
    for u in units:
        cur.execute("DELETE FROM units WHERE id = ?", (u.id,))
        cur.execute(
            """INSERT INTO units
               (id, theme, kind, ref, title, text, source_id, source_name,
                source_url, retrieved, legal_version, licence, lang)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (u.id, u.theme, u.kind, u.ref, u.title, u.text, u.source_id,
             u.source_name, u.source_url, u.retrieved, u.legal_version, u.licence,
             u.lang),
        )
        for a in u.assets:
            cur.execute(
                "INSERT INTO assets (unit_id, type, path, caption) VALUES (?,?,?,?)",
                (u.id, a.type, a.path, a.caption))
        for ref_id in u.cross_refs:
            cur.execute(
                "INSERT INTO cross_refs (unit_id, ref_id) VALUES (?,?)",
                (u.id, ref_id))
    conn.commit()


def set_meta(conn: sqlite3.Connection, **kv: str) -> None:
    cur = conn.cursor()
    for k, v in kv.items():
        cur.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?,?)", (k, str(v)))
    conn.commit()


def unit_to_json(u: KnowledgeUnit) -> dict:
    d = asdict(u)
    return d


def export_json(conn: sqlite3.Connection, path: str) -> int:
    """Dump the whole KB to a single JSON file (Phase-2 friendly, diffable)."""
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM units ORDER BY source_id, ref").fetchall()
    out = []
    for r in rows:
        rd = dict(r)
        rd["assets"] = [dict(a) for a in conn.execute(
            "SELECT type, path, caption FROM assets WHERE unit_id=?", (r["id"],))]
        rd["cross_refs"] = [x[0] for x in conn.execute(
            "SELECT ref_id FROM cross_refs WHERE unit_id=?", (r["id"],))]
        out.append(rd)
    meta = {k: v for k, v in conn.execute("SELECT key, value FROM meta")}
    conn.row_factory = None
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"meta": meta, "units": out}, fh, ensure_ascii=False, indent=2)
    return len(out)
