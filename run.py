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
import sqlite3
import sys

from src import fetch, parse as parse_stage, normalize as normalize_stage
from src.sources import SOURCES, BY_ID
from src.themes import THEMES

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "kb.sqlite")
JSON_PATH = os.path.join(os.path.dirname(__file__), "data", "kb.json")
QDB_PATH = os.path.join(os.path.dirname(__file__), "data", "questions.sqlite")
QJSON_PATH = os.path.join(os.path.dirname(__file__), "data", "questions.json")


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


def cmd_questions(args):
    """Phase 2: generate the question bank from the KB (templated figures for now)."""
    from src.questions import figures, schema as qschema
    if not os.path.exists(DB_PATH):
        sys.exit("no knowledge base — run `python run.py build` first")
    kb = sqlite3.connect(DB_PATH)
    kb_version = next((v for k, v in kb.execute("SELECT key, value FROM meta")
                       if k == "kb_version"), "")

    print("→ generate figure-recognition questions")
    qs, stats = figures.build_figure_questions(kb)
    kb.close()

    if os.path.exists(QDB_PATH):      # clean rebuild (deterministic, like normalize)
        os.remove(QDB_PATH)
    conn = qschema.connect(QDB_PATH)
    cfg = qschema.ExamConfig()        # Vaud/Léman defaults (cantonal — configurable)
    qschema.set_meta(conn, kb_version=kb_version, generated=_dt.date.today().isoformat(),
                     generators=figures.GENERATOR,
                     exam_questions=cfg.questions, total_points=cfg.total_points,
                     points_per_question=cfg.points_per_question,
                     pass_points=cfg.pass_points, time_limit_min=cfg.time_limit_min,
                     scoring=cfg.scoring, canton=cfg.canton_default)
    qschema.write_questions(conn, qs)
    n_export = qschema.export_json(conn, QJSON_PATH, exportable_only=True)
    conn.close()

    print(f"\n✓ question bank built: {QDB_PATH}")
    print(f"  {stats['generated']} questions generated  (exported: {n_export})")
    print(f"  distractors: {stats['by_strategy']}")
    print("  by theme:")
    for tid, label in THEMES.items():
        if stats["by_theme"].get(tid):
            print(f"     {stats['by_theme'][tid]:4}  {label}")
    print(f"  skipped: {stats['not_recognizable']} non-atomic captions, "
          f"{stats['no_distractors']} lacking distractors, "
          f"{stats['non_public']} non-public-domain "
          f"(of {stats['figures']} figures)")


def cmd_web(args):
    """Package the exported bank into a self-contained static site under web/
    (deployable to GitHub Pages): web/questions.json + web/assets/ with image
    paths rewritten relative to the page. The HTML/CSS/JS are committed source."""
    import json
    import shutil
    if not os.path.exists(QJSON_PATH):
        sys.exit("no question bank — run `python run.py questions` first")
    web = os.path.join(os.path.dirname(__file__), "web")
    assets_out = os.path.join(web, "assets")
    if os.path.exists(assets_out):
        shutil.rmtree(assets_out)

    data = json.load(open(QJSON_PATH, encoding="utf-8"))
    copied = 0

    def relocate(p: str | None) -> str | None:
        nonlocal copied
        if not p:
            return p
        rel = p[len("data/"):] if p.startswith("data/") else p   # assets/<src>/<f>
        src = os.path.join(os.path.dirname(__file__), p)
        dst = os.path.join(web, rel)
        if os.path.exists(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            copied += 1
        return rel

    for q in data["questions"]:
        q["image"] = relocate(q.get("image"))
        for c in q["choices"]:
            c["image"] = relocate(c.get("image"))
    with open(os.path.join(web, "questions.json"), "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)

    print(f"✓ static site bundled: {web}/")
    print(f"  {len(data['questions'])} questions · {copied} images copied")
    print(f"  preview: python -m http.server -d web 8000  →  http://localhost:8000")


def main():
    ap = argparse.ArgumentParser(description="Boat-permit pipeline")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("fetch", "parse", "build"):
        p = sub.add_parser(name)
        p.add_argument("--force", action="store_true", help="ignore the raw cache")
        p.add_argument("--only", help="comma-separated source ids")
    sub.add_parser("questions", help="generate the Phase-2 question bank from the KB")
    sub.add_parser("web", help="bundle the bank into the static web/ player")
    args = ap.parse_args()
    {"fetch": cmd_fetch, "parse": cmd_parse, "build": cmd_build,
     "questions": cmd_questions, "web": cmd_web}[args.cmd](args)


if __name__ == "__main__":
    main()
