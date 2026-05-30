#!/usr/bin/env python3
"""Boat-permit knowledge-base pipeline (Phase 1).

Three independently re-runnable stages, each reading the previous stage's
on-disk output:

    python run.py fetch              # pull raw sources -> data/raw/  (cached)
    python run.py parse              # raw -> structured units (prints a summary)
    python run.py build              # fetch (if needed) + parse + normalize -> SQLite
    python run.py build --force      # re-fetch everything, ignoring the cache

Build writes data/kb.sqlite (+ data/kb.json). Use --only <id,id> to limit to
specific sources (ids: oni, rnl, matelotage_wp, meteo_vents, meteo_signaux, geneve).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import sys

from src import fetch, parse as parse_stage, normalize as normalize_stage
from src.sources import SOURCES, BY_ID
from src.themes import THEMES

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "kb.sqlite")
JSON_PATH = os.path.join(os.path.dirname(__file__), "data", "kb.json")


def _select(only: str | None):
    if not only:
        return SOURCES
    ids = [x.strip() for x in only.split(",") if x.strip()]
    missing = [i for i in ids if i not in BY_ID]
    if missing:
        sys.exit(f"unknown source id(s): {', '.join(missing)}")
    return [BY_ID[i] for i in ids]


def cmd_fetch(args):
    srcs = _select(args.only)
    man = fetch.fetch_all(srcs, force=args.force)
    for sid, m in man.items():
        keys = m.get("files", m.get("pages", {}))
        n_img = len(m.get("files", {}).get("images", {})) if "files" in m else 0
        extra = f" (+{n_img} images)" if n_img else ""
        print(f"  fetched {sid:16} version={m.get('legal_version','')!r}{extra}")


def cmd_parse(args):
    srcs = _select(args.only)
    parsed = parse_stage.parse_all(srcs)
    total = 0
    for sid, units in parsed.items():
        kinds = {}
        for u in units:
            kinds[u.kind] = kinds.get(u.kind, 0) + 1
        total += len(units)
        print(f"  parsed {sid:16} {len(units):4} units  {kinds}")
    print(f"  total: {total} units")
    return parsed


def cmd_build(args):
    srcs = _select(args.only)
    print("→ fetch")
    fetch.fetch_all(srcs, force=args.force)
    print("→ parse")
    parsed = parse_stage.parse_all(srcs)
    print("→ normalize")
    version = _dt.date.today().isoformat()
    stats = normalize_stage.normalize(parsed, DB_PATH, version, json_path=JSON_PATH)

    print(f"\n✓ knowledge base built: {DB_PATH}")
    print(f"  version {version} · {stats['units']} units · {stats['assets']} assets")
    print(f"  by source: {stats['by_source']}")
    print(f"  by kind:   {stats['by_kind']}")
    print("  by theme:")
    for tid, label in THEMES.items():
        print(f"     {stats['by_theme'].get(tid, 0):4}  {label}")
    if stats["themes_missing"]:
        print(f"  ⚠ themes with no units: {stats['themes_missing']}")


def main():
    ap = argparse.ArgumentParser(description="Boat-permit KB pipeline (Phase 1)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("fetch", "parse", "build"):
        p = sub.add_parser(name)
        p.add_argument("--force", action="store_true", help="ignore the raw cache")
        p.add_argument("--only", help="comma-separated source ids")
    args = ap.parse_args()
    {"fetch": cmd_fetch, "parse": cmd_parse, "build": cmd_build}[args.cmd](args)


if __name__ == "__main__":
    main()
