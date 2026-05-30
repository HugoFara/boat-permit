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


def _langs(args) -> list[str]:
    """Requested content languages, FR by default. FR pulls/parses every source;
    DE/IT cover only the law (fedlex) sources."""
    raw = (getattr(args, "lang", None) or "fr").split(",")
    return [x.strip() for x in raw if x.strip()]


def cmd_fetch(args):
    srcs = _select(args.only)
    langs = _langs(args)
    man = {}
    if "fr" in langs:                       # FR pulls every source (law + refs)
        man.update(fetch.fetch_all(srcs, force=args.force))
    extra = [l for l in langs if l != "fr"]  # DE/IT pull only the law sources
    if extra:
        man.update(fetch.fetch_fedlex_langs(extra, srcs, force=args.force))
    for sid, m in man.items():
        n_img = len(m.get("files", {}).get("images", {})) if "files" in m else 0
        tail = f" (+{n_img} images)" if n_img else ""
        lang = m.get("lang", "fr")
        print(f"  fetched {sid:18} [{lang}] version={m.get('legal_version','')!r}{tail}")


def cmd_parse(args):
    srcs = _select(args.only)
    parsed = parse_stage.parse_all(srcs, langs=tuple(_langs(args)))
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
    langs = _langs(args)
    print("→ fetch")
    if "fr" in langs:
        fetch.fetch_all(srcs, force=args.force)
    extra = [l for l in langs if l != "fr"]
    if extra:
        fetch.fetch_fedlex_langs(extra, srcs, force=args.force)
    print("→ parse")
    parsed = parse_stage.parse_all(srcs, langs=tuple(langs))
    print("→ normalize")
    version = _dt.date.today().isoformat()
    stats = normalize_stage.normalize(parsed, DB_PATH, version, json_path=JSON_PATH)

    print(f"\n✓ knowledge base built: {DB_PATH}")
    print(f"  version {version} · {stats['units']} units · {stats['assets']} assets")
    print(f"  by lang:   {stats['by_lang']}")
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

    conn = qschema.connect(QDB_PATH)
    # Re-generate only the templated figure questions; preserve any LLM/reviewed
    # drafts in the bank (cascade clears their choices automatically).
    conn.execute("DELETE FROM questions WHERE generator LIKE 'tmpl:%'")
    conn.commit()
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


def cmd_draft(args):
    """Phase-2 step 5: LLM-draft questions for the prose/law themes into the bank
    as `pending` (held behind the review gate). Needs a built bank from
    `run.py questions`; uses the Anthropic API (ANTHROPIC_API_KEY)."""
    from src.questions import prose, schema as qschema
    if not os.path.exists(DB_PATH):
        sys.exit("no knowledge base — run `python run.py build` first")
    themes = ([t.strip() for t in args.theme.split(",")] if args.theme
              else list(prose.PROSE_THEMES))
    kb = sqlite3.connect(DB_PATH)

    if args.seed:           # load the hand-authored curated seed (no API call)
        from src.questions import seed_prose
        qs, st = prose.seed_questions(kb, seed_prose.SEED)
        kb.close()
        conn = qschema.connect(QDB_PATH)
        qschema.write_questions(conn, qs)
        qschema.export_json(conn, QJSON_PATH, exportable_only=True)
        status = qschema.counts_by_status(conn)
        conn.close()
        print(f"✓ seed loaded: {st['kept']}/{st['entries']} questions added as PENDING "
              f"({st['weak_grounding']} weak-grounding, {st['invalid']} invalid, "
              f"{st['missing_unit']} missing unit)")
        print(f"  bank by status: {status}")
        print("  review with: python run.py review --list")
        return

    if args.dry_run:        # show the prompt the model would receive, no API call
        for t in themes:
            units = prose.select_units(kb, t, limit=1)
            if units:
                print(f"--- prompt for {t} / {units[0]['ref']} ---\n")
                print(prose.build_prompt(units[0], args.per_unit))
                break
        return

    try:
        drafter = prose.AnthropicDrafter(model=args.model)
    except ImportError:
        sys.exit("install the SDK: pip install anthropic")
    except Exception as e:
        sys.exit(f"cannot init Anthropic client (set ANTHROPIC_API_KEY): {e}")

    allq, totals = [], {"kept": 0, "drafted": 0, "weak_grounding": 0, "invalid": 0}
    for t in themes:
        print(f"→ drafting {t} …")
        qs, st = prose.draft_for_theme(kb, drafter, t, limit=args.limit,
                                       per_unit=args.per_unit)
        allq += qs
        for k in totals:
            totals[k] += st.get(k, 0)
        print(f"    {st['kept']} kept / {st['drafted']} drafted "
              f"({st['weak_grounding']} weak-grounding, {st['invalid']} invalid)")
    kb.close()

    conn = qschema.connect(QDB_PATH)
    qschema.write_questions(conn, allq)
    qschema.export_json(conn, QJSON_PATH, exportable_only=True)
    status = qschema.counts_by_status(conn)
    conn.close()
    print(f"\n✓ {totals['kept']} drafts added as PENDING → {QDB_PATH}")
    print(f"  bank by status: {status}")
    print("  review with: python run.py review --list")


def cmd_review(args):
    """Operate the review gate: list pending drafts (with a grounding score), or
    approve/reject by id. Approved questions reach the public bank on next build."""
    from src.questions import prose, schema as qschema
    if not os.path.exists(QDB_PATH):
        sys.exit("no question bank — run `python run.py questions` first")
    conn = qschema.connect(QDB_PATH)

    if args.approve or args.reject:
        n = qschema.set_review_status(conn, args.approve or [], "approved")
        n += qschema.set_review_status(conn, args.reject or [], "rejected")
        conn.commit()
        print(f"updated {n} question(s); bank by status: {qschema.counts_by_status(conn)}")
        conn.close()
        return

    if args.list:
        kb = sqlite3.connect(DB_PATH) if os.path.exists(DB_PATH) else None
        src_text = {}
        if kb is not None:
            kb.row_factory = sqlite3.Row
            src_text = {r["id"]: r["text"]
                        for r in kb.execute("SELECT id, text FROM units")}
        pending = qschema.load_questions(conn, review_status="pending")
        pending = [q for q in pending if not args.theme or q.theme == args.theme]
        for q in pending:
            g = prose.grounding_score(
                " ".join(c.text for c in q.choices if c.is_correct),
                src_text.get(q.provenance.unit_id, ""))
            print(f"\n[{q.id}]  {q.theme} · {q.provenance.ref}  (grounding {g})")
            print(f"  {q.stem}")
            for c in q.choices:
                print(f"    {'[x]' if c.is_correct else '[ ]'} {c.text}")
            print(f"    → {q.explanation}")
        print(f"\n{len(pending)} pending. Approve: "
              f"python run.py review --approve <id> [<id> …]")
        conn.close()
        return

    print(f"bank by status: {qschema.counts_by_status(conn)}")
    conn.close()


def cmd_web(args):
    """Package the exported bank into a self-contained static site under web/
    (deployable to GitHub Pages): web/questions.json + web/assets/ with image
    paths rewritten relative to the page. The HTML/CSS/JS are committed source."""
    import json
    import shutil
    from src.questions import schema as qschema
    if not os.path.exists(QDB_PATH):
        sys.exit("no question bank — run `python run.py questions` first")
    conn = qschema.connect(QDB_PATH)
    web = os.path.join(os.path.dirname(__file__), "web")
    assets_out = os.path.join(web, "assets")
    if os.path.exists(assets_out):
        shutil.rmtree(assets_out)
    copied = 0

    def relocate(p: str | None) -> str | None:
        """Copy a data/-relative asset into web/ and return its page-relative path."""
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

    def bundle(out_name: str, lang: str | None) -> int:
        """Export one bank file (optionally language-filtered), rewrite its image
        paths into web/, and write it under web/<out_name>."""
        # lang=None exports the canonical data/questions.json (kept); per-language
        # exports go to a throwaway temp that's removed once bundled.
        tmp = QJSON_PATH if lang is None else f"{QJSON_PATH}.{lang}.tmp"
        n = qschema.export_json(conn, tmp, exportable_only=True, lang=lang)
        data = json.load(open(tmp, encoding="utf-8"))
        if lang is not None:
            os.remove(tmp)
        for q in data["questions"]:
            q["image"] = relocate(q.get("image"))
            for c in q["choices"]:
                c["image"] = relocate(c.get("image"))
        with open(os.path.join(web, out_name), "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        return n

    # Canonical/back-compat bundle (all exportable questions, every language) +
    # one per-language bundle the player prefers, with a manifest for the switcher.
    total = bundle("questions.json", None)
    langs = qschema.languages_present(conn, exportable_only=True)
    per_lang = {}
    for lg in langs:
        per_lang[lg] = bundle(f"questions.{lg}.json", lg)
    manifest = {
        "default": qschema.DEFAULT_LANG,
        "supported": sorted(qschema.LANGS),
        "available": {lg: {"count": per_lang[lg],
                           "unofficial": lg not in qschema.GROUNDED_LANGS}
                      for lg in langs},
    }
    with open(os.path.join(web, "languages.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    conn.close()

    print(f"✓ static site bundled: {web}/")
    print(f"  {total} questions · {copied} images copied")
    print(f"  languages with content: {', '.join(f'{lg}({per_lang[lg]})' for lg in langs) or 'none'}")
    print(f"  preview: python -m http.server -d web 8000  →  http://localhost:8000")


def main():
    ap = argparse.ArgumentParser(description="Boat-permit pipeline")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("fetch", "parse", "build"):
        p = sub.add_parser(name)
        p.add_argument("--force", action="store_true", help="ignore the raw cache")
        p.add_argument("--only", help="comma-separated source ids")
        p.add_argument("--lang", default="fr",
                       help="comma-separated content languages (fr,de,it); "
                            "non-fr covers the law (fedlex) sources only")
    sub.add_parser("questions", help="generate the Phase-2 question bank from the KB")

    d = sub.add_parser("draft", help="LLM-draft prose/law questions (pending review)")
    d.add_argument("--theme", help="comma-separated themes (default: all prose themes)")
    d.add_argument("--limit", type=int, default=0, help="max units per theme")
    d.add_argument("--per-unit", type=int, default=2, help="questions per unit")
    d.add_argument("--model", default="claude-sonnet-4-6")
    d.add_argument("--dry-run", action="store_true", help="print a prompt, no API call")
    d.add_argument("--seed", action="store_true",
                   help="load the curated hand-authored seed instead of calling the API")

    r = sub.add_parser("review", help="operate the review gate over drafts")
    r.add_argument("--list", action="store_true", help="list pending drafts")
    r.add_argument("--theme", help="filter the listing to one theme")
    r.add_argument("--approve", nargs="+", metavar="ID", help="approve question id(s)")
    r.add_argument("--reject", nargs="+", metavar="ID", help="reject question id(s)")

    sub.add_parser("web", help="bundle the bank into the static web/ player")
    args = ap.parse_args()
    {"fetch": cmd_fetch, "parse": cmd_parse, "build": cmd_build,
     "questions": cmd_questions, "draft": cmd_draft, "review": cmd_review,
     "web": cmd_web}[args.cmd](args)


if __name__ == "__main__":
    main()
