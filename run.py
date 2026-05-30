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
import json
import os
import sqlite3
import sys

from src import countries, fetch, parse as parse_stage, normalize as normalize_stage

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "kb.sqlite")
JSON_PATH = os.path.join(os.path.dirname(__file__), "data", "kb.json")
QDB_PATH = os.path.join(os.path.dirname(__file__), "data", "questions.sqlite")
QJSON_PATH = os.path.join(os.path.dirname(__file__), "data", "questions.json")


def _qpaths(code: str) -> tuple[str, str]:
    """Question-bank output paths for a country. CH keeps the original
    (back-compat) filenames; other countries are namespaced (questions.de.sqlite)
    so building one country never clobbers another's bank."""
    data = os.path.join(os.path.dirname(__file__), "data")
    if code == countries.DEFAULT:
        return QDB_PATH, QJSON_PATH
    s = code.lower()
    return (os.path.join(data, f"questions.{s}.sqlite"),
            os.path.join(data, f"questions.{s}.json"))


def _country(args):
    """The active country (default CH ⇒ the original Swiss build, unchanged)."""
    return countries.get(getattr(args, "country", None))


def _select(only: str | None, country):
    srcs = list(country.sources)
    by_id = {s.id: s for s in srcs}
    if not only:
        return srcs
    ids = [x.strip() for x in only.split(",") if x.strip()]
    missing = [i for i in ids if i not in by_id]
    if missing:
        sys.exit(f"unknown source id(s) for {country.code}: {', '.join(missing)}")
    return [by_id[i] for i in ids]


def _langs(args, country) -> list[str]:
    """Requested content languages; the country's default when unspecified. Law
    acts are fetched/parsed once per language; language-specific references only
    when their own language is requested."""
    raw = (getattr(args, "lang", None) or country.default_lang).split(",")
    return [x.strip() for x in raw if x.strip()]


def cmd_fetch(args):
    country = _country(args)
    srcs = _select(args.only, country)
    langs = _langs(args, country)
    man = fetch.fetch_for_langs(langs, srcs, force=args.force)
    for sid, m in man.items():
        n_img = len(m.get("files", {}).get("images", {})) if "files" in m else 0
        tail = f" (+{n_img} images)" if n_img else ""
        lang = m.get("lang", "fr")
        print(f"  fetched {sid:18} [{lang}] version={m.get('legal_version','')!r}{tail}")


def cmd_parse(args):
    country = _country(args)
    srcs = _select(args.only, country)
    parsed = parse_stage.parse_all(srcs, langs=tuple(_langs(args, country)))
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
    country = _country(args)
    srcs = _select(args.only, country)
    langs = _langs(args, country)
    print(f"→ fetch  [country {country.code}]")
    fetch.fetch_for_langs(langs, srcs, force=args.force)
    print("→ parse")
    parsed = parse_stage.parse_all(srcs, langs=tuple(langs))
    print("→ normalize")
    version = _dt.date.today().isoformat()
    stats = normalize_stage.normalize(
        parsed, DB_PATH, version, json_path=JSON_PATH,
        themes_table=country.themes, extension_themes=country.extension_themes,
        base_lang=country.default_lang, country_code=country.code)

    print(f"\n✓ knowledge base built: {DB_PATH}")
    print(f"  country {country.code} · version {version} · "
          f"{stats['units']} units · {stats['assets']} assets")
    print(f"  by lang:   {stats['by_lang']}")
    print(f"  by source: {stats['by_source']}")
    print(f"  by kind:   {stats['by_kind']}")
    if stats.get("themes_propagated"):
        print(f"  themes propagated to sibling languages: {stats['themes_propagated']}")
    print("  by theme:")
    for tid, label in country.themes.items():
        print(f"     {stats['by_theme'].get(tid, 0):4}  {label}")
    if stats["themes_missing"]:
        print(f"  ⚠ themes with no units: {stats['themes_missing']}")


def cmd_questions(args):
    """Phase 2: build the question bank. Switzerland generates templated figure
    questions from its KB; Germany ingests the official ELWIS catalogues verbatim
    (see _questions_de). Default (no --country) is the unchanged Swiss path."""
    country = _country(args)
    if country.code == "DE":
        return _questions_de(args, country)

    from src.questions import figures, schema as qschema
    if not os.path.exists(DB_PATH):
        sys.exit("no knowledge base — run `python run.py build` first")
    kb = sqlite3.connect(DB_PATH)
    kb_meta = {k: v for k, v in kb.execute("SELECT key, value FROM meta")}
    kb_version = kb_meta.get("kb_version", "")
    theme_labels = countries.get(kb_meta.get("country", "CH")).themes

    print("→ generate figure-recognition questions")
    qs, stats = figures.build_figure_questions(kb)
    kb.close()

    conn = qschema.connect(QDB_PATH)
    # Re-generate only the templated figure questions; preserve any LLM/reviewed
    # drafts in the bank (cascade clears their choices automatically).
    conn.execute("DELETE FROM questions WHERE generator LIKE 'tmpl:%'")
    conn.commit()
    # cat-A default / cat-D adds voile; canton overlays the time limit (GE default).
    cfg = qschema.profile(getattr(args, "permis", "A"), getattr(args, "canton", None))
    qschema.set_meta(conn, kb_version=kb_version, generated=_dt.date.today().isoformat(),
                     generators=figures.GENERATOR,
                     exam_questions=cfg.questions, total_points=cfg.total_points,
                     points_per_question=cfg.points_per_question,
                     pass_points=cfg.pass_points, time_limit_min=cfg.time_limit_min,
                     scoring=cfg.scoring, canton=cfg.canton_default,
                     canton_code=cfg.canton_code,
                     permis=cfg.permis, permis_label=cfg.label)
    qschema.write_questions(conn, qs)
    n_export = qschema.export_json(conn, QJSON_PATH, exportable_only=True)
    conn.close()

    print(f"\n✓ question bank built: {QDB_PATH}")
    print(f"  {stats['generated']} questions generated  (exported: {n_export})")
    print(f"  distractors: {stats['by_strategy']}")
    print("  by theme:")
    for tid, label in theme_labels.items():
        if stats["by_theme"].get(tid):
            print(f"     {stats['by_theme'][tid]:4}  {label}")
    print(f"  skipped: {stats['not_recognizable']} non-atomic captions, "
          f"{stats['no_distractors']} lacking distractors, "
          f"{stats['non_public']} non-public-domain "
          f"(of {stats['figures']} figures)")


def _de_block_rules(country) -> dict:
    """Per-permit block pass-minima, keyed by the ingested questions' block ids, so
    the block-aware web player and schema.grade_exam_blocks can grade a German
    sitting. Only the federal SBF permits that draw on the ELWIS catalogue are
    included (the voluntary/Bodensee permits have no public MC catalogue), and only
    those with at least one enforceable per-block minimum (drops the sail-only
    Binnen permit, which the law scores on an overall total we don't model)."""
    from src.questions import elwis
    rules = {}
    for code, p in country.permits.items():
        e = p.exam
        if not (e.questions and e.blocks):
            continue
        mapped = [{"block": elwis.BLOCK_NAME_TO_ID.get(b.name, b.name),
                   "count": b.count, "min_correct": b.min_correct} for b in e.blocks]
        if not all(b["block"] in elwis.BLOCK_NAME_TO_ID.values() for b in mapped):
            continue
        if not any(b["min_correct"] > 0 for b in mapped):
            continue
        rules[code] = {"label": p.label, "questions": e.questions,
                       "time_limit_min": e.time_limit_min, "blocks": mapped}
    return rules


def _questions_de(args, country):
    """Build the German bank from the official ELWIS Fragenkataloge (SBF Binnen +
    See), verbatim and §5-attributed, with German themes + exam blocks. Needs no
    KB — the catalogue is the source — and writes a country-namespaced bank."""
    from src.questions import elwis, schema as qschema
    from src.countries import de_themes

    print("→ ingest official ELWIS catalogues (Binnen + See) — verbatim, §5(2)")
    qs, stats = elwis.ingest(force=getattr(args, "force", False))

    qdb, qjson = _qpaths(country.code)
    conn = qschema.connect(qdb)
    # Re-ingest only the ELWIS questions; leave any other drafts in place.
    conn.execute("DELETE FROM questions WHERE generator LIKE 'elwis:%'")
    conn.commit()
    qschema.set_meta(
        conn, country=country.code, kb_version="",
        generated=_dt.date.today().isoformat(), generators=elwis.GENERATOR,
        catalogue_version="2023-08", scoring="blocks",
        licence=elwis.LICENCE, source="ELWIS (WSV des Bundes) — www.elwis.de",
        block_rules=json.dumps(_de_block_rules(country), ensure_ascii=False),
        # German UI chrome for the shared web player (read via app.js S()).
        ui_title="Sportbootführerschein — Theorie (Übung)",
        ui_h1="Sportbootführerschein — Theorieprüfung",
        ui_subtitle="Freies Lernwerkzeug · die amtlichen ELWIS-Fragenkataloge "
                    "(SBF Binnen + See), wörtlich übernommen. Kein amtlicher Test.",
        ui_demo="<strong>Wähle deine Führerscheinart.</strong> Die Prüfung ist "
                "blockweise aufgebaut (Basisfragen + spezifische Fragen) — jeder "
                "Block hat ein eigenes Bestehensminimum.",
        ui_sourcenote="Quelle: amtliche Fragenkataloge der Wasserstraßen- und "
                      "Schifffahrtsverwaltung des Bundes (www.elwis.de), wörtlich "
                      "und mit Quellenangabe wiedergegeben (§5(2) UrhG). "
                      "Bundesrecht ist gemeinfrei (§5(1) UrhG).")
    qschema.write_questions(conn, qs, is_valid_theme=de_themes.is_valid)
    n_export = qschema.export_json(conn, qjson, exportable_only=True)
    conn.close()

    print(f"\n✓ German question bank built: {qdb}")
    print(f"  {stats['total']} questions ingested  (exported: {n_export})  "
          f"[{stats['basis_deduped']} shared Basisfragen deduped]")
    print(f"  by catalogue: {stats['by_catalogue']}")
    print(f"  by block: {stats['by_block']}  ·  {stats['with_image']} with a figure")
    print("  by theme:")
    for tid, label in country.themes.items():
        if stats["by_theme"].get(tid):
            print(f"     {stats['by_theme'][tid]:4}  {label}")
    print(f"  bundle to web: deferred (player country switcher) — JSON at {qjson}")


def _draft_themes(country) -> list[str]:
    """Default themes to draft for a country. Switzerland keeps the curated prose
    theme list (signalisation is templated figures, not drafted); other countries
    draft every theme in their taxonomy (units with no prose text just yield none)."""
    if country.code == countries.DEFAULT:
        from src.questions import prose
        return list(prose.PROSE_THEMES)
    return list(country.themes)


def cmd_draft(args):
    """Phase-2 step 5: LLM-draft questions for the prose/law themes into the bank
    as `pending` (held behind the review gate). Needs a built bank from
    `run.py questions`; uses the Anthropic API (ANTHROPIC_API_KEY). Drafting is
    per country + language: `--country INT` over the COLREG bank drafts English
    questions, `--country DE` drafts German, etc. (default: the Swiss French bank)."""
    from src.questions import prose, schema as qschema
    country = _country(args)
    qdb, qjson = _qpaths(country.code)
    lang = getattr(args, "lang", None) or country.default_lang
    if not os.path.exists(DB_PATH):
        sys.exit("no knowledge base — run `python run.py build` first")
    themes = ([t.strip() for t in args.theme.split(",")] if args.theme
              else _draft_themes(country))
    kb = sqlite3.connect(DB_PATH)

    valid_theme = country.themes.__contains__   # validate against THIS country's taxonomy
    if args.seed:           # load the hand-authored curated seed (no API call)
        from src.questions import seed_prose
        qs, st = prose.seed_questions(kb, seed_prose.SEED, is_valid_theme=valid_theme)
        kb.close()
        conn = qschema.connect(qdb)
        qschema.write_questions(conn, qs, is_valid_theme=valid_theme)
        # Seeds load as PENDING by design; re-apply any recorded review decisions
        # so a rebuilt bank keeps its approvals/rejections (durable, committed).
        from src.questions import seed_review
        applied = seed_review.apply(conn)
        conn.commit()
        qschema.export_json(conn, qjson, exportable_only=True)
        status = qschema.counts_by_status(conn)
        conn.close()
        print(f"✓ seed loaded: {st['kept']}/{st['entries']} questions added as PENDING "
              f"({st['weak_grounding']} weak-grounding, {st['invalid']} invalid, "
              f"{st['missing_unit']} missing unit)")
        print(f"  ledger re-applied: {applied['approved']} approved, {applied['rejected']} rejected")
        print(f"  bank by status: {status}")
        print("  review with: python run.py review --list")
        return

    if args.dry_run:        # show the prompt the model would receive, no API call
        for t in themes:
            units = prose.select_units(kb, t, limit=1, lang=lang)
            if units:
                print(f"--- prompt for {t} / {units[0]['ref']} [{lang}] ---\n")
                print(prose.build_prompt(units[0], args.per_unit, lang))
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
        print(f"→ drafting {t} [{lang}] …")
        qs, st = prose.draft_for_theme(kb, drafter, t, limit=args.limit,
                                       per_unit=args.per_unit, lang=lang,
                                       is_valid_theme=valid_theme)
        allq += qs
        for k in totals:
            totals[k] += st.get(k, 0)
        print(f"    {st['kept']} kept / {st['drafted']} drafted "
              f"({st['weak_grounding']} weak-grounding, {st['invalid']} invalid)")
    kb.close()

    conn = qschema.connect(qdb)
    qschema.write_questions(conn, allq, is_valid_theme=valid_theme)
    qschema.export_json(conn, qjson, exportable_only=True)
    status = qschema.counts_by_status(conn)
    conn.close()
    print(f"\n✓ {totals['kept']} drafts added as PENDING → {qdb}")
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
        # Record the decision durably: questions.sqlite is regenerable, so the
        # ledger is what survives a rebuild (see src/questions/seed_review.py).
        from src.questions import seed_review
        seed_review.record({**{i: "approved" for i in (args.approve or [])},
                            **{i: "rejected" for i in (args.reject or [])}})
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


def cmd_fr(args):
    """Build the French *permis plaisance* banks (option côtière + eaux intérieures)
    and bundle their static players under web/fr/. France is seed-driven (no Fedlex
    fetch/parse), so this is self-contained — see src/fr/ and docs/france.md."""
    from src.fr import build_fr
    stats = build_fr.build()
    print(f"✓ France banks built + bundled: {build_fr.FR_WEB}/")
    print(f"  generated {stats['generated']}")
    for option, s in stats["options"].items():
        core = ", ".join(f"{b}({n})" for b, n in s.get("core", {}).items()) or "—"
        print(f"  {option:18} {s['questions_fr']} FR · {s['questions_en']} EN  "
              f"(themes: {len(s['themes'])}; core: {core}; "
              f"anki {','.join(s['anki']) or '—'}; gift {','.join(s['gift']) or '—'})")
    print(f"  preview: python -m http.server -d web 8000  →  "
          f"http://localhost:8000/fr/")


def _player_html_de(nav: str) -> str:
    """A German player page reusing the shared engine (../app.js, ../i18n.js).
    Mirrors web/index.html's DOM so the engine drives it unchanged; the German
    chrome + theme labels come from the bank meta (ui_*) and i18n.js."""
    return f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Sportbootführerschein — Theorie (Übung)</title>
  <link rel="stylesheet" href="../style.css">
</head>
<body>
<nav class="countrybar" aria-label="country">{nav}</nav>
<nav id="langbar" aria-label="language"></nav>
<main id="app">
  <section id="screen-start" class="screen">
    <h1 id="t-h1"></h1>
    <p class="sub" id="t-subtitle"></p>
    <div id="loop-proof" class="banner"></div>
    <div id="fallback-note" class="banner soft hidden"></div>
    <div id="config-summary" class="config"></div>
    <div class="domains-block">
      <span id="t-pool" class="domains-label"></span>
      <div id="pools" class="domains"></div>
    </div>
    <div class="domains-block">
      <span id="t-domains" class="domains-label"></span>
      <div id="domains" class="domains"></div>
    </div>
    <div class="domains-block">
      <span id="t-canton" class="domains-label"></span>
      <div id="cantons" class="domains"></div>
    </div>
    <div class="actions">
      <button id="btn-exam" class="primary"></button>
      <button id="btn-practice"></button>
    </div>
    <p class="fine" id="t-sourcenote"></p>
    <div id="anki-dl" class="anki-dl hidden"></div>
  </section>
  <section id="screen-quiz" class="screen hidden">
    <header class="quizbar">
      <span id="progress"></span>
      <span id="timer" class="timer hidden"></span>
    </header>
    <div id="question"></div>
    <div class="actions">
      <button id="btn-action" class="primary"></button>
    </div>
  </section>
  <section id="screen-results" class="screen hidden">
    <h2 id="t-resulttitle"></h2>
    <div id="score"></div>
    <div id="breakdown" class="breakdown"></div>
    <div class="actions">
      <button id="btn-restart" class="primary"></button>
    </div>
    <h3 id="t-correction"></h3>
    <div id="review"></div>
  </section>
</main>
<footer class="sitefoot">
  <span id="t-foottagline"></span> ·
  <span id="meta-foot"></span>
</footer>
<script src="../i18n.js"></script>
<script src="../app.js"></script>
</body>
</html>
"""


def _build_de_web(web: str, core_avail: dict | None = None) -> dict | None:
    """Bundle the German bank into web/de/ (its own questions + manifest + index),
    reusing the shared player engine. `core_avail` is the global harmonised-core
    manifest (from cmd_web) so the DE player can offer the pooled CEVNI/COLREGS core.
    Returns a small stats dict, or None if the DE bank hasn't been built (run
    `python run.py questions --country DE` first)."""
    import shutil
    from src.questions import schema as qschema
    qdb, _ = _qpaths("DE")
    if not os.path.exists(qdb):
        return None
    web_de = os.path.join(web, "de")
    assets_out = os.path.join(web_de, "assets")
    if os.path.exists(assets_out):
        shutil.rmtree(assets_out)
    os.makedirs(web_de, exist_ok=True)
    conn = qschema.connect(qdb)
    copied = 0

    def relocate(p):
        nonlocal copied
        if not p:
            return p
        rel = p[len("data/"):] if p.startswith("data/") else p
        src = os.path.join(os.path.dirname(__file__), p)
        dst = os.path.join(web_de, rel)
        if os.path.exists(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            copied += 1
        return rel

    def bundle(out_name, lang):
        tmp = os.path.join(web_de, f"_{out_name}.tmp")
        qschema.export_json(conn, tmp, exportable_only=True, lang=lang)
        data = json.load(open(tmp, encoding="utf-8"))
        os.remove(tmp)
        for q in data["questions"]:
            q["image"] = relocate(q.get("image"))
            for c in q["choices"]:
                c["image"] = relocate(c.get("image"))
        with open(os.path.join(web_de, out_name), "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        return len(data["questions"])

    total = bundle("questions.json", None)          # back-compat (all langs = de)
    n_de = bundle("questions.de.json", "de")         # the player's preferred bundle
    meta = {k: v for k, v in conn.execute("SELECT key, value FROM meta")}
    conn.close()

    # The permit picker + block grading read these from the manifest. Each permit
    # also carries its track (inland/maritime) so the player composes the right
    # harmonised core (CEVNI for Binnen, COLREGS for See).
    from src import jurisdictions
    track_of = {p.code: jurisdictions.permit_track(p)
                for p in countries.get("DE").permits.values()}
    block_rules = json.loads(meta.get("block_rules", "{}"))
    permits = [{"code": code, "track": track_of.get(code, "inland"), **rule}
               for code, rule in block_rules.items()]
    # The German player consumes the GLOBAL harmonised core built by cmd_web (at the
    # web/ root): its German-language base bundles, referenced one level up. So an
    # SBF-See learner studies the pooled COLREGS core (DE See + any other sea bank).
    de_core = {}
    for base, per in (core_avail or {}).items():
        if "de" in per:
            de_core[base] = {"de": {"path": "../" + per["de"]["path"],
                                    "count": per["de"]["count"]}}
    manifest = {
        "default": "de", "supported": ["de"],
        "available": {"de": {"count": n_de, "unofficial": False}},
        "permits": permits,
        "regions": [{"code": "national", "name": "Bundesweit (SBF See/Binnen)",
                     "primary": True}],
        "country_default": "DE",
        "core": de_core,
    }
    with open(os.path.join(web_de, "languages.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)

    nav = ('<a href="../">🇨🇭 Suisse</a> · <a href="../fr/">🇫🇷 France</a> · '
           '<span class="on">🇩🇪 Deutschland</span>')
    with open(os.path.join(web_de, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(_player_html_de(nav))
    return {"questions": n_de, "permits": len(permits), "copied": copied}


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

    def bundle(out_name: str, lang: str | None, keep_ids: set | None = None,
               pool: str | None = None) -> int:
        """Export one bank file (optionally language-filtered), rewrite its image
        paths into web/, and write it under web/<out_name>.

        `keep_ids`, when given, restricts the bundle to those question ids and
        stamps `meta.pool = pool` — used for the harmonised-core base sub-bundles
        (universal/cevni/colregs). National bundles pass `keep_ids=None` and are
        therefore written exactly as before."""
        # lang=None exports the canonical data/questions.json (kept); per-language
        # exports go to a throwaway temp that's removed once bundled.
        tmp = QJSON_PATH if lang is None else f"{QJSON_PATH}.{lang}.tmp"
        n = qschema.export_json(conn, tmp, exportable_only=True, lang=lang)
        data = json.load(open(tmp, encoding="utf-8"))
        if lang is not None:
            os.remove(tmp)
        if keep_ids is not None:
            data["questions"] = [q for q in data["questions"] if q["id"] in keep_ids]
            data["meta"]["pool"] = pool
        for q in data["questions"]:
            q["image"] = relocate(q.get("image"))
            for c in q["choices"]:
                c["image"] = relocate(c.get("image"))
        with open(os.path.join(web, out_name), "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        return len(data["questions"])

    # Canonical/back-compat bundle (all exportable questions, every language) +
    # one per-language bundle the player prefers, with a manifest for the switcher.
    total = bundle("questions.json", None)
    langs = qschema.languages_present(conn, exportable_only=True)
    per_lang = {}
    for lg in langs:
        per_lang[lg] = bundle(f"questions.{lg}.json", lg)
    # Harmonised core — the GLOBAL, cross-country portable subset. We pool the
    # base-scoped questions (universal / cevni / colregs) from EVERY question bank
    # (CH here + DE + the per-option FR banks), so a learner studies the merged
    # harmonised material — the German SBF-See and the French côtière COLREGS
    # questions together — not just one country's. Pooled per (base, language) and
    # deduped by id; the four national questions.<lang>.json above stay
    # byte-identical (this only adds questions.<base>.<lang>.json). Scope is derived
    # by src/scope.py, never stored. COLREGS is grounded in the canonical 1972 text
    # (the INT layer — public-domain USCG reproduction); CEVNI via national inland
    # enactments (its UNECE text is not redistributable).
    #   NOTE: the pool is language-bounded — a German See question enters a French
    #   learner's core only once translated; until then each language's core is the
    #   union of that language's banks.
    import glob as _glob
    from src import scope
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    bank_paths = sorted(_glob.glob(os.path.join(data_dir, "questions*.sqlite")))
    _GROUNDING = {
        "colregs": "COLREG — International Regulations for Preventing Collisions at "
                   "Sea, 1972 (canonical, USCG public-domain) + national transpositions.",
        "cevni": "National inland-navigation enactments implementing CEVNI "
                 "(the UNECE CEVNI text is not redistributable).",
        "universal": "Portable seamanship — valid under any code.",
    }
    pooled: dict[str, dict] = {b: {} for b in scope.BASES}    # base -> lang -> [qdict]
    seen: dict[str, set] = {b: set() for b in scope.BASES}
    pooled_counts = {b: 0 for b in scope.BASES}
    overlay_counts = {"national": 0, "local": 0}
    for bp in bank_paths:
        bconn = qschema.connect(bp)
        bq = [q for q in qschema.load_questions(bconn)
              if q.review_status in qschema.EXPORTABLE_STATUSES]
        id_scope = {q.id: scope.classify(q) for q in bq}
        for s in id_scope.values():
            if s in overlay_counts:
                overlay_counts[s] += 1
        for lg in qschema.languages_present(bconn, exportable_only=True):
            tmp = f"{QJSON_PATH}.pool.{lg}.tmp"
            qschema.export_json(bconn, tmp, exportable_only=True, lang=lg)
            data = json.load(open(tmp, encoding="utf-8"))
            os.remove(tmp)
            for qd in data["questions"]:
                base = id_scope.get(qd["id"])
                if base not in scope.BASES or qd["id"] in seen[base]:
                    continue
                seen[base].add(qd["id"])
                qd["image"] = relocate(qd.get("image"))
                for c in qd["choices"]:
                    c["image"] = relocate(c.get("image"))
                pooled[base].setdefault(lg, []).append(qd)
                pooled_counts[base] += 1
        bconn.close()
    core_avail: dict[str, dict] = {}                  # {base: {lang: {path, count}}}
    core_langs: set = set()
    for base in scope.BASES:
        per: dict[str, dict] = {}
        for lg, qs in sorted(pooled[base].items()):
            path = f"questions.{base}.{lg}.json"
            payload = {"meta": {"lang": lg, "pool": base, "scope": base,
                                "unofficial": lg not in qschema.GROUNDED_LANGS,
                                "generated": _dt.date.today().isoformat(),
                                "grounding": _GROUNDING.get(base, "")},
                       "questions": qs}
            with open(os.path.join(web, path), "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
            per[lg] = {"path": path, "count": len(qs)}
            core_langs.add(lg)
        if per:
            core_avail[base] = per

    from src import cantons, countries, jurisdictions
    # The country dimension (above canton) is owned by the src/countries registry
    # (CH built natively, DE by the German agent). Read it here for display only —
    # code/name/langs/permits/regions — so the player's picker stays populated from
    # the live registry rather than a copy.
    # Only playable (permit-bearing) countries belong in the player's picker; the
    # supra-national INT layer is sourcing-only (no permits, no bank) so it is
    # excluded here even though it is a full registry member.
    country_manifest = [{
        "code": c.code, "name": c.name, "default_lang": c.default_lang,
        "langs": list(c.langs),
        "permits": [{"code": p.code, "label": p.label,
                     "track": jurisdictions.permit_track(p)}
                    for p in c.permits.values()],
        "regions": c.region_manifest(),
    } for c in (countries.get(code) for code in countries.codes()) if c.permits]
    manifest = {
        "default": qschema.DEFAULT_LANG,
        "supported": sorted(qschema.LANGS),
        "available": {lg: {"count": per_lang[lg],
                           "unofficial": lg not in qschema.GROUNDED_LANGS}
                      for lg in langs},
        # Per-canton variance for the player's canton picker (single source of
        # truth: src/cantons.py). Content/pass mark are national; the timer varies.
        "cantons": cantons.as_manifest(),
        "canton_default": cantons.DEFAULT_CANTON,
        # Country registry (the dimension above canton) + the harmonised-core pool,
        # split by base (universal/cevni/colregs) per language. The player composes
        # the available bases into one "common core" pool (src/scope.py).
        "countries": country_manifest,
        "country_default": countries.DEFAULT,
        "core": core_avail,
    }
    # Offline-study downloads: Anki decks (.apkg + editable .tsv) and a Moodle
    # GIFT file, one set per language, for the in-page download links.
    from tools import anki, gift
    anki_dir = os.path.join(web, "anki")
    gift_dir = os.path.join(web, "gift")
    for d in (anki_dir, gift_dir):
        if os.path.exists(d):
            shutil.rmtree(d)
    anki_avail, gift_avail = {}, {}
    for lg in langs:
        n, n_img = anki.export_to(conn, anki_dir, lg)
        if n:
            anki_avail[lg] = {"apkg": f"anki/boat-permit.{lg}.apkg",
                              "tsv": f"anki/boat-permit.{lg}.tsv",
                              "count": n, "images": n_img}
        ng = gift.export_to(conn, gift_dir, lg)
        if ng:
            gift_avail[lg] = {"gift": f"gift/boat-permit.{lg}.gift", "count": ng}
    manifest["anki"] = anki_avail
    manifest["gift"] = gift_avail

    with open(os.path.join(web, "languages.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    conn.close()

    print(f"✓ static site bundled: {web}/")
    print(f"  {total} questions · {copied} images copied")
    anki_summary = ", ".join(f"{lg}({anki_avail[lg]['count']})" for lg in anki_avail)
    print(f"  Anki decks: {anki_summary or 'none'} · GIFT: {', '.join(gift_avail) or 'none'}")
    print(f"  languages with content: {', '.join(f'{lg}({per_lang[lg]})' for lg in langs) or 'none'}")
    core_summary = ", ".join(f"{b}({pooled_counts[b]})" for b in scope.BASES
                             if pooled_counts[b])
    colregs_lang = ", ".join(f"{lg}:{e['count']}"
                             for lg, e in sorted(core_avail.get("colregs", {}).items()))
    print(f"  global harmonised core (pooled over {len(bank_paths)} banks): "
          f"{core_summary or 'none'}  ·  overlays: national({overlay_counts['national']}) "
          f"local({overlay_counts['local']})")
    print(f"  colregs core per language: {colregs_lang or 'none'}")
    print(f"  countries: {', '.join(countries.codes())}  ·  "
          f"jurisdictions: {len(jurisdictions.codes())} regimes")

    # Germany: its own bundle under web/de/ (reuses ../app.js + ../i18n.js), with
    # the permit picker + block-based exam. Emitted only once the DE bank is built.
    de = _build_de_web(web, core_avail)
    if de:
        print(f"  🇩🇪 web/de/: {de['questions']} questions · "
              f"{de['permits']} permits · {de['copied']} images")
    else:
        print("  🇩🇪 web/de/: skipped (run `python run.py questions --country DE`)")
    print(f"  preview: python -m http.server -d web 8000  →  http://localhost:8000")


def main():
    ap = argparse.ArgumentParser(description="Boat-permit pipeline")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("fetch", "parse", "build"):
        p = sub.add_parser(name)
        p.add_argument("--force", action="store_true", help="ignore the raw cache")
        p.add_argument("--only", help="comma-separated source ids")
        p.add_argument("--country", default=countries.DEFAULT, choices=countries.codes(),
                       help=f"country to build (default {countries.DEFAULT}); "
                            "DE pulls the German SBF law (gesetze-im-internet.de)")
        p.add_argument("--lang",
                       help="comma-separated content languages; defaults to the "
                            "country's (CH: fr,de,it / DE: de). Law acts are "
                            "fetched once per language")
    q = sub.add_parser("questions", help="generate the Phase-2 question bank from the KB")
    q.add_argument("--country", default=countries.DEFAULT, choices=countries.codes(),
                   help=f"country bank to build (default {countries.DEFAULT}); "
                        "DE ingests the official ELWIS catalogues verbatim")
    q.add_argument("--force", action="store_true",
                   help="re-fetch the source catalogue, ignoring the cache (DE)")
    q.add_argument("--permis", default="A", choices=["A", "D"],
                   help="recreational permit profile: A (motorboat, default) or "
                        "D (sailing — adds the voile theme; scaffolded, no source yet)")
    from src import cantons as _cantons
    q.add_argument("--canton", default=_cantons.DEFAULT_CANTON,
                   choices=sorted(_cantons.CANTONS),
                   help="canton whose variance (exam time limit) to stamp as the "
                        f"build default; the player lets users switch (default: "
                        f"{_cantons.DEFAULT_CANTON})")

    d = sub.add_parser("draft", help="LLM-draft prose/law questions (pending review)")
    d.add_argument("--country", default=countries.DEFAULT, choices=countries.codes(),
                   help=f"country whose bank to draft into (default {countries.DEFAULT}); "
                        "INT drafts COLREG (en), DE drafts the German law, etc.")
    d.add_argument("--lang", help="content language to draft (default: the country's "
                                  "default language)")
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
    sub.add_parser("fr", help="build the France permis plaisance banks + web/fr/ "
                              "players (seed-driven; see docs/france.md)")
    args = ap.parse_args()
    {"fetch": cmd_fetch, "parse": cmd_parse, "build": cmd_build,
     "questions": cmd_questions, "draft": cmd_draft, "review": cmd_review,
     "web": cmd_web, "fr": cmd_fr}[args.cmd](args)


if __name__ == "__main__":
    main()
