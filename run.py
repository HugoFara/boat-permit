#!/usr/bin/env python3
"""Boating-licence knowledge-base pipeline (Phase 1).

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
from src import validate as _validate

DATA = os.path.join(os.path.dirname(__file__), "data")


def _kbpaths(code: str) -> tuple[str, str]:
    """Per-country knowledge-base paths (kb.<code>.sqlite / .json). Per-country so
    building one country's KB never clobbers another's — no shared scratch file."""
    s = code.lower()
    return (os.path.join(DATA, f"kb.{s}.sqlite"),
            os.path.join(DATA, f"kb.{s}.json"))


def _qpaths(code: str) -> tuple[str, str]:
    """Per-country question-bank paths (questions.<code>.sqlite / .json). Every
    country is namespaced by its code — no country gets an unprefixed name."""
    s = code.lower()
    return (os.path.join(DATA, f"questions.{s}.sqlite"),
            os.path.join(DATA, f"questions.{s}.json"))


def _country(args):
    """The active country (default INT ⇒ the harmonised/international layer)."""
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
    parsed = parse_stage.parse_all(srcs, langs=tuple(langs), tagger=country.tagger)
    print("→ normalize")
    version = _dt.date.today().isoformat()
    kb_db, kb_json = _kbpaths(country.code)
    stats = normalize_stage.normalize(
        parsed, kb_db, version, json_path=kb_json,
        themes_table=country.themes, extension_themes=country.extension_themes,
        base_lang=country.default_lang, country_code=country.code)

    print(f"\n✓ knowledge base built: {kb_db}")
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
    if country.code != "CH":
        sys.exit(f"`questions` builds the Swiss templated-figure bank (CH) or the "
                 f"German catalogue (DE); for {country.code} draft prose with "
                 f"`python tools/subagent_draft.py ingest <lang> {country.code}`.")

    from src.questions import figures, schema as qschema
    kb_db, _ = _kbpaths(country.code)
    qdb, qjson = _qpaths(country.code)
    if not os.path.exists(kb_db):
        sys.exit("no knowledge base — run `python run.py build` first")
    kb = sqlite3.connect(kb_db)
    kb_meta = {k: v for k, v in kb.execute("SELECT key, value FROM meta")}
    kb_version = kb_meta.get("kb_version", "")
    theme_labels = countries.get(kb_meta.get("country") or countries.DEFAULT).themes

    print("→ generate figure-recognition questions")
    qs, stats = figures.build_figure_questions(kb)
    kb.close()

    conn = qschema.connect(qdb)
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
    n_export = qschema.export_json(conn, qjson, exportable_only=True)
    conn.close()

    print(f"\n✓ question bank built: {qdb}")
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
    from src.countries import de_themes
    # ELWIS (federal SBF) block names + the BSO-seeded Bodensee Sachgebiet names,
    # so both the catalogue permits and the Bodensee-Schifferpatent resolve.
    name_to_id = {**elwis.BLOCK_NAME_TO_ID, **de_themes.BODENSEE_BLOCK_NAME_TO_ID}
    rules = {}
    for code, p in country.permits.items():
        e = p.exam
        if not (e.questions and e.blocks):
            continue
        mapped = [{"block": name_to_id.get(b.name, b.name),
                   "count": b.count, "min_correct": b.min_correct} for b in e.blocks]
        if not all(b["block"] in name_to_id.values() for b in mapped):
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
    if country.code == "CH":
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
    kb_db, _ = _kbpaths(country.code)
    lang = getattr(args, "lang", None) or country.default_lang
    if not os.path.exists(kb_db):
        sys.exit("no knowledge base — run `python run.py build` first")
    themes = ([t.strip() for t in args.theme.split(",")] if args.theme
              else _draft_themes(country))
    kb = sqlite3.connect(kb_db)

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
    country = _country(args)
    qdb, _ = _qpaths(country.code)
    kb_db, _ = _kbpaths(country.code)
    if not os.path.exists(qdb):
        sys.exit(f"no question bank for {country.code} — build it first")
    conn = qschema.connect(qdb)

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
        kb = sqlite3.connect(kb_db) if os.path.exists(kb_db) else None
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


def _player_html(lang: str, nav: str, title: str) -> str:
    """A player page reusing the shared engine (../app.js, ../i18n.js) from a
    country sub-bundle (web/<code>/). Mirrors the player DOM so the engine drives
    it unchanged; chrome + theme labels come from the bank meta (ui_*) and i18n.js."""
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
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
    <div id="coverage-note" class="banner soft hidden"></div>
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
      <span id="t-permit" class="domains-label"></span>
      <div id="permits" class="domains"></div>
      <p id="permit-note" class="fine"></p>
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
    <details id="permit-path" class="permit-path hidden">
      <summary id="t-pathtitle"></summary>
      <p class="fine" id="t-pathintro"></p>
      <div id="path-steps"></div>
    </details>
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


# The cross-country nav shown at the top of every player. From a country
# sub-bundle (web/<code>/) the landing is one level up (prefix "../"); the France
# option players sit one level deeper, so they pass prefix "../../".
_COUNTRY_NAV = [("", "🏠 Accueil"), ("int", "🌍 Code commun"), ("ch", "🇨🇭 Suisse"),
                ("de", "🇩🇪 Deutschland"), ("fr", "🇫🇷 France")]


def _countrybar(active: str, prefix: str = "../") -> str:
    parts = []
    for code, label in _COUNTRY_NAV:
        if code == active:
            parts.append(f'<span class="on">{label}</span>')
        else:
            parts.append(f'<a href="{prefix}{code + "/" if code else ""}">{label}</a>')
    return " · ".join(parts)


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

    _learn_layer(conn, web_de, ["de"])               # principle tags + concept cards
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
        # Path-to-permit steps, scoped by permit (federal SBF vs Bodensee). The
        # player filters by the active permit; additive — questions.de.json unchanged.
        "path": countries.get("DE").path_manifest(),
        # DE IS the official ELWIS catalogue — the yardstick, not a derived bank.
        # The player shows a high-confidence note rather than a coverage figure.
        "coverage": {"official": True},
        "core": de_core,
    }
    with open(os.path.join(web_de, "languages.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)

    title = meta.get("ui_title") or "Sportbootführerschein — Theorie (Übung)"
    with open(os.path.join(web_de, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(_player_html("de", _countrybar("de"), title))
    return {"questions": n_de, "permits": len(permits), "copied": copied}


def _learn_layer(conn, out_dir, langs):
    """Roadmap group A/D1 plumbing, run per bundle:
      * tag every question with its generative ``principle`` (deterministic, in
        place) so the tag ships inside the question JSON via export_json;
      * export any review-cleared concept "why" cards per language.
    Concept files are written only when content exists — an empty bank ships no
    file and the player just shows no Learn card (graceful, still 100% offline).
    Must run BEFORE the question export so the principle tag is present."""
    from src.questions import schema as qschema
    from src.questions import principles as principlesmod
    principlesmod.tag_questions(conn)
    for lg in langs:
        tmp = os.path.join(out_dir, f"_concepts.{lg}.tmp")
        n = qschema.export_concepts_json(conn, tmp, lg, exportable_only=True)
        dst = os.path.join(out_dir, f"concepts.{lg}.json")
        if n:
            os.replace(tmp, dst)
        elif os.path.exists(tmp):
            os.remove(tmp)


def _build_ch_web(web: str, core_avail: dict | None = None) -> dict | None:
    """Bundle the Swiss bank into web/ch/ — multilingual (fr/de/it + unofficial en),
    canton picker (no permits), Anki/GIFT downloads, and the shared common-core
    toggle. Chrome comes from i18n.js STRINGS (no ui_* override). Returns stats or
    None if the CH bank isn't built."""
    import shutil
    from src.questions import schema as qschema
    from src import cantons
    from tools import anki, gift
    qdb, _ = _qpaths("CH")
    if not os.path.exists(qdb):
        return None
    web_ch = os.path.join(web, "ch")
    for sub in ("assets", "anki", "gift"):
        d = os.path.join(web_ch, sub)
        if os.path.exists(d):
            shutil.rmtree(d)
    os.makedirs(web_ch, exist_ok=True)
    conn = qschema.connect(qdb)
    copied = 0

    def relocate(p):
        nonlocal copied
        if not p:
            return p
        rel = p[len("data/"):] if p.startswith("data/") else p
        src = os.path.join(os.path.dirname(__file__), p)
        dst = os.path.join(web_ch, rel)
        if os.path.exists(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            copied += 1
        return rel

    def bundle(out_name, lang):
        tmp = os.path.join(web_ch, f"_{out_name}.tmp")
        qschema.export_json(conn, tmp, exportable_only=True, lang=lang)
        data = json.load(open(tmp, encoding="utf-8"))
        os.remove(tmp)
        for q in data["questions"]:
            q["image"] = relocate(q.get("image"))
            for c in q["choices"]:
                c["image"] = relocate(c.get("image"))
        with open(os.path.join(web_ch, out_name), "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        return len(data["questions"])

    langs = qschema.languages_present(conn, exportable_only=True)
    _learn_layer(conn, web_ch, langs)    # principle tags + concept cards (before export)
    total = bundle("questions.json", None)
    per_lang = {lg: bundle(f"questions.{lg}.json", lg) for lg in langs}

    anki_dir, gift_dir = os.path.join(web_ch, "anki"), os.path.join(web_ch, "gift")
    anki_avail, gift_avail = {}, {}
    for lg in langs:
        n, n_img = anki.export_to(conn, anki_dir, lg)
        if n:
            anki_avail[lg] = {"apkg": f"anki/boating-licence.{lg}.apkg",
                              "tsv": f"anki/boating-licence.{lg}.tsv",
                              "count": n, "images": n_img}
        ng = gift.export_to(conn, gift_dir, lg)
        if ng:
            gift_avail[lg] = {"gift": f"gift/boating-licence.{lg}.gift", "count": ng}
    conn.close()

    # Recreational categories (cat-A motorboat, cat-D sailing). Unlike Germany's
    # block-scored SBF permits, these share ONE point-scored theory paper, so the
    # picker is informational: it names the category + its mandatory threshold (the
    # note) without changing the pool — until the cat-D `voile` study theme lands.
    # Labels/notes are localised player-side by code (i18n permit_<code>); the
    # `label`/`note` here are the FR fallback. The player honours these only when
    # the bank is point-scored, so emitting them is harmless for the canton picker.
    from src import jurisdictions
    ch_country = countries.get("CH")
    ch_permits = ch_country.permits
    permits = [{
        "code": p.code,
        "drive": p.drive,
        "track": jurisdictions.permit_track(p),
        "label": p.label,
        "note": p.note,
        "questions": p.exam.questions,
        "mandatory": p.mandatory,
        "themes": list(p.themes),
    } for p in ch_permits.values()]
    manifest = {
        "default": qschema.DEFAULT_LANG,
        "supported": sorted(qschema.LANGS),
        "available": {lg: {"count": per_lang[lg],
                           "unofficial": lg not in qschema.GROUNDED_LANGS}
                      for lg in langs},
        "permits": permits,
        # Themes that are study-only (NOT on the official theory exam): the player
        # shows them as a study domain for permits that include them, but keeps them
        # out of exam-mode draws. CH: `voile` for cat-D.
        "extension_themes": sorted(ch_country.extension_themes),
        # Path-to-permit scaffolding: the non-theory steps (age/medical/practical/
        # application/fees/validity) rendered in the player's "how to get the
        # licence" panel. Additive — does not touch questions.<lang>.json.
        "path": ch_country.path_manifest(),
        "cantons": cantons.as_manifest(),
        "canton_default": cantons.DEFAULT_CANTON,
        "core": _core_refs(core_avail, sorted(qschema.LANGS)),
        # Honest catalogue-coverage banner: derived-bank measured coverage vs the
        # official German catalogue, from the committed lock (same source as the
        # docs). None when not yet measured → the player simply hides the banner.
        "coverage": _validate.load_lock().get("banks", {}).get("CH"),
        "anki": anki_avail, "gift": gift_avail,
    }
    with open(os.path.join(web_ch, "languages.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    title = "Permis bateau Léman — examen théorique (entraînement)"
    with open(os.path.join(web_ch, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(_player_html("fr", _countrybar("ch"), title))
    return {"questions": total, "langs": list(langs), "copied": copied,
            "anki": list(anki_avail), "gift": list(gift_avail)}


def _build_int_web(web: str, core_avail: dict | None = None) -> dict | None:
    """Bundle the INT/COLREG bank into web/int/ — a small English player on the
    harmonised maritime code (COLREG 1972, USCG public domain) plus the shared
    common-core toggle (defaulting to the COLREGS core). No cantons, no permits.
    The COLREG bank carries no exam meta, so a simple practice config is stamped in.
    Returns stats or None if the INT bank isn't built."""
    import shutil
    from src.questions import schema as qschema
    qdb, _ = _qpaths("INT")
    if not os.path.exists(qdb):
        return None
    web_int = os.path.join(web, "int")
    assets_out = os.path.join(web_int, "assets")
    if os.path.exists(assets_out):
        shutil.rmtree(assets_out)
    os.makedirs(web_int, exist_ok=True)
    conn = qschema.connect(qdb)
    copied = 0

    def relocate(p):
        nonlocal copied
        if not p:
            return p
        rel = p[len("data/"):] if p.startswith("data/") else p
        src = os.path.join(os.path.dirname(__file__), p)
        dst = os.path.join(web_int, rel)
        if os.path.exists(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            copied += 1
        return rel

    def bundle(out_name, lang):
        tmp = os.path.join(web_int, f"_{out_name}.tmp")
        n = qschema.export_json(conn, tmp, exportable_only=True, lang=lang)
        data = json.load(open(tmp, encoding="utf-8"))
        os.remove(tmp)
        cap = min(30, n) or n
        data["meta"].update({
            "ui_title": "COLREG 1972 — collision regulations (practice)",
            "ui_h1": "COLREG 1972 — international collision regulations",
            "ui_subtitle": "International Regulations for Preventing Collisions at "
                           "Sea, 1972 — practice (not an official exam).",
            "ui_sourcenote": "Source: COLREG 1972 · USCG Navigation Rules "
                             "(public domain, 17 U.S.C. §105).",
            "exam_questions": cap, "total_points": cap, "points_per_question": 1,
            "pass_points": int(cap * 0.8), "time_limit_min": 30,
            "scoring": "all_or_nothing", "canton": "", "canton_code": "",
        })
        for q in data["questions"]:
            q["image"] = relocate(q.get("image"))
            for c in q["choices"]:
                c["image"] = relocate(c.get("image"))
        with open(os.path.join(web_int, out_name), "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        return len(data["questions"])

    _learn_layer(conn, web_int, ["en"])  # principle tags + concept cards (before export)
    bundle("questions.json", None)
    n_en = bundle("questions.en.json", "en")
    conn.close()
    manifest = {
        "default": "en", "supported": ["en"],
        "available": {"en": {"count": n_en, "unofficial": False}},
        "core": _core_refs(core_avail, ["en"]),
        "default_track": "maritime",
    }
    with open(os.path.join(web_int, "languages.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    with open(os.path.join(web_int, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(_player_html("en", _countrybar("int"),
                              "COLREG 1972 — collision regulations (practice)"))
    return {"questions": n_en, "copied": copied}


def _core_refs(core_avail: dict | None, langs: list[str]) -> dict:
    """Rewrite the shared harmonised-core manifest for a country sub-bundle: keep
    the given languages, point each base bundle one level up (the core JSON lives
    at the web/ root, shared by all players)."""
    out: dict[str, dict] = {}
    for base, per in (core_avail or {}).items():
        entry = {lg: {"path": "../" + per[lg]["path"], "count": per[lg]["count"]}
                 for lg in langs if lg in per}
        if entry:
            out[base] = entry
    return out


def cmd_web(args):
    """Bundle the static site under web/. The root web/ is a country-picker landing
    (committed source); each country is its own player sub-bundle (web/ch, web/de,
    web/int; France via `run.py fr`) reusing the shared engine (web/app.js,
    i18n.js, style.css). The GLOBAL harmonised core (questions.<base>.<lang>.json
    + its images in web/assets/) lives at the root and is shared by every player,
    referenced one level up as ../."""
    import json
    import shutil
    import glob as _glob
    from src.questions import schema as qschema
    from src import scope, countries, jurisdictions
    web = os.path.join(os.path.dirname(__file__), "web")
    assets_out = os.path.join(web, "assets")
    if os.path.exists(assets_out):
        shutil.rmtree(assets_out)
    # Remove stale root artifacts from the pre-restructure CH-at-root layout: the
    # national bundles + manifest + Anki/GIFT now live under web/ch/, and web/
    # index.html is the committed landing. (The shared core questions.<base>.<lang>
    # .json and web/assets/ are rebuilt below.)
    for stale in (["questions.json", "languages.json"]
                  + [f"questions.{lg}.json" for lg in qschema.LANGS]):
        sp = os.path.join(web, stale)
        if os.path.exists(sp):
            os.remove(sp)
    for d in ("anki", "gift"):
        dp = os.path.join(web, d)
        if os.path.exists(dp):
            shutil.rmtree(dp)
    copied = 0

    def relocate_core(p):
        """Copy a core-question image into the SHARED web/assets/ (root) and return
        a ../-relative path, so every country sub-bundle (web/<code>/) resolves it
        to the one shared copy."""
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
        return "../" + rel

    # Harmonised core — the GLOBAL, cross-country portable subset, pooled from EVERY
    # bank (CH + DE + INT + the per-option FR banks) per (base, language) and deduped
    # by id. Scope is derived by src/scope.py, never stored. Lives at the web/ root
    # (questions.<base>.<lang>.json + shared images in web/assets/); each player
    # references it via ../. COLREGS is grounded in the canonical 1972 text (the INT
    # layer — public-domain USCG reproduction); CEVNI via national inland enactments.
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
    pool_tmp = os.path.join(data_dir, "_pool.tmp")
    for bp in bank_paths:
        bconn = qschema.connect(bp)
        bq = [q for q in qschema.load_questions(bconn)
              if q.review_status in qschema.EXPORTABLE_STATUSES]
        id_scope = {q.id: scope.classify(q) for q in bq}
        for s in id_scope.values():
            if s in overlay_counts:
                overlay_counts[s] += 1
        for lg in qschema.languages_present(bconn, exportable_only=True):
            qschema.export_json(bconn, pool_tmp, exportable_only=True, lang=lg)
            data = json.load(open(pool_tmp, encoding="utf-8"))
            os.remove(pool_tmp)
            for qd in data["questions"]:
                base = id_scope.get(qd["id"])
                if base not in scope.BASES or qd["id"] in seen[base]:
                    continue
                seen[base].add(qd["id"])
                qd["image"] = relocate_core(qd.get("image"))
                for c in qd["choices"]:
                    c["image"] = relocate_core(c.get("image"))
                pooled[base].setdefault(lg, []).append(qd)
                pooled_counts[base] += 1
        bconn.close()
    core_avail: dict[str, dict] = {}                  # {base: {lang: {path, count}}}
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
        if per:
            core_avail[base] = per

    print(f"✓ static site bundled: {web}/  (landing = web/index.html, committed)")
    core_summary = ", ".join(f"{b}({pooled_counts[b]})" for b in scope.BASES
                             if pooled_counts[b])
    print(f"  global harmonised core (pooled over {len(bank_paths)} banks): "
          f"{core_summary or 'none'} · {copied} core images → web/assets/ · "
          f"overlays national({overlay_counts['national']}) local({overlay_counts['local']})")

    # Per-country player sub-bundles (each reuses ../app.js + ../i18n.js).
    ch = _build_ch_web(web, core_avail)
    if ch:
        print(f"  🇨🇭 web/ch/: {ch['questions']} questions · "
              f"langs {','.join(ch['langs'])} · {ch['copied']} images · "
              f"anki {','.join(ch['anki']) or '—'} gift {','.join(ch['gift']) or '—'}")
    else:
        print("  🇨🇭 web/ch/: skipped (run `python run.py questions --country CH`)")
    intl = _build_int_web(web, core_avail)
    if intl:
        print(f"  🌍 web/int/: {intl['questions']} COLREG questions (en) + common core")
    else:
        print("  🌍 web/int/: skipped (build the INT/COLREG bank first)")
    de = _build_de_web(web, core_avail)
    if de:
        print(f"  🇩🇪 web/de/: {de['questions']} questions · "
              f"{de['permits']} permits · {de['copied']} images")
    else:
        print("  🇩🇪 web/de/: skipped (run `python run.py questions --country DE`)")
    print(f"  countries: {', '.join(countries.codes())} · "
          f"jurisdictions: {len(jurisdictions.codes())} regimes")
    print(f"  France: run `python run.py fr` (web/fr/). "
          f"Preview: python -m http.server -d web 8000  →  http://localhost:8000")


def cmd_validate(args):
    """Cross-check the derived CH/FR common core against the official German
    catalogue on shared harmonised scope. Default: deterministic coverage. With
    --deep: an LLM divergence flagger (costs tokens; emits pairs for human review)."""
    from src import validate
    if not args.deep:
        print(validate.format_coverage(validate.coverage()))
        return
    if args.dry_run:
        n = [0]
        validate.flag_divergences(args.bank, base=args.base, limit=args.limit,
                                  on_prompt=lambda p: (print(p, "\n" + "─" * 60),
                                                       n.__setitem__(0, n[0] + 1)))
        print(f"\n[dry-run] {n[0]} prompt(s) would be sent — no API call made.")
        return
    flags = validate.flag_divergences(args.bank, base=args.base, limit=args.limit)
    if not flags:
        print(f"No divergences flagged in {args.bank} {args.base} "
              f"(checked up to {args.limit}).")
        return
    print(f"{len(flags)} divergence(s) flagged for review "
          f"({args.bank} vs official DE, {args.base}):\n")
    for f in flags:
        print(f"  [{f['verdict']}] {f['concept']} · {f['question_id']}")
        print(f"    {f['stem']}")
        print(f"    → {f['reason']}\n")


# --- path-to-permit doc rendering --------------------------------------------
# The country deep-dive docs carry a "from theory to licence" section generated
# from the SAME data as the player (`Country.path`) — single source of truth, so
# the prose can never drift from the manifest. `python run.py path-docs` rewrites
# the marked block; tests/test_path.py asserts the committed docs are in sync.
_PATH_DOC_LANG = {"CH": "fr", "DE": "de", "FR": "fr"}
_PATH_DOC_FILE = {"CH": "switzerland.md", "DE": "germany.md", "FR": "france.md"}
_PATH_STEP_LABELS = {        # mirrors web/i18n.js PATH_STRINGS step labels
    "fr": {"age": "Âge minimum", "medical": "Vue & aptitude médicale",
           "first_aid": "Premiers secours", "practical": "Examen pratique",
           "application": "Demande & inscription", "fees": "Émoluments",
           "validity": "Validité & renouvellement"},
    "de": {"age": "Mindestalter", "medical": "Sehtest & ärztliche Eignung",
           "first_aid": "Nothilfe", "practical": "Praktische Prüfung",
           "application": "Gesuch & Anmeldung", "fees": "Gebühren",
           "validity": "Gültigkeit & Erneuerung"},
}
_PATH_DOC_CHROME = {
    "fr": {"heading": "Du théorique au permis : les étapes hors examen",
           "intro": "Réussir la théorie ne suffit pas. Ces étapes sont générées "
                    "depuis `src/countries/{mod}.py` (champ `path`) — chaque fait "
                    "est tiré d'une source officielle et daté.",
           "step": "Étape", "detail": "Détail", "scope": "Portée",
           "source": "Source", "verified": "vérifié le", "volatile": "(peut varier)"},
    "de": {"heading": "Von der Theorie zum Ausweis: die Schritte neben der Prüfung",
           "intro": "Die Theorie zu bestehen genügt nicht. Diese Schritte werden aus "
                    "`src/countries/{mod}.py` (Feld `path`) generiert — jeder Fakt "
                    "stammt aus einer offiziellen Quelle und ist datiert.",
           "step": "Schritt", "detail": "Detail", "scope": "Geltung",
           "source": "Quelle", "verified": "geprüft am", "volatile": "(kann sich ändern)"},
}
_PATH_DOC_START = ("<!-- path:auto:start — generated by `python run.py path-docs`; "
                   "do not edit by hand -->")
_PATH_DOC_END = "<!-- path:auto:end -->"


def _path_scope_tag(step: dict) -> str:
    """A short portability tag for the doc's scope column: a region code (CH fees →
    GE), or the DE regime (Bodensee vs the federal SBF); empty when the step is
    country-wide and applies to every permit."""
    if step["region_scope"]:
        return step["region_scope"]
    ps = step["permit_scope"]
    if not ps:
        return ""
    return "Bodensee" if any(c.startswith("Bodensee") for c in ps) else "SBF"


def _path_doc_section(code: str) -> str:
    """Render one country's path-to-permit table in its doc language, from the same
    `Country.path` the player reads. Returns the markdown (without the markers)."""
    country = countries.get(code)
    lang = _PATH_DOC_LANG[code]
    ch = _PATH_DOC_CHROME[lang]
    labels = _PATH_STEP_LABELS[lang]
    steps = country.path_manifest()
    has_scope = any(_path_scope_tag(s) for s in steps)
    cols = [ch["step"], ch["detail"]] + ([ch["scope"]] if has_scope else []) + [ch["source"]]
    lines = [f"## {ch['heading']}", "",
             ch["intro"].replace("{mod}", code.lower()), "",
             "| " + " | ".join(cols) + " |",
             "|" + "|".join(["---"] * len(cols)) + "|"]
    for s in steps:
        label = labels.get(s["code"], s["code"])
        body = (s["body"].get(lang) or s["body"].get(country.default_lang)
                or next(iter(s["body"].values()), ""))
        body = body.replace("\n", " ").replace("|", "\\|")
        vol = f" {ch['volatile']}" if s["volatile"] else ""
        src = f"[{s['source']}]({s['url']})" if s["url"] else s["source"]
        src = f"{src} · {ch['verified']} {s['as_of']}"
        row = [f"**{label}**{vol}", body] + ([_path_scope_tag(s)] if has_scope else []) + [src]
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def cmd_path_docs(args):
    """Rewrite the generated path-to-permit block in each country doc, in sync with
    `Country.path`. Idempotent: re-run after editing a country's `path`."""
    docs_dir = os.path.join(os.path.dirname(__file__), "docs")
    changed = []
    for code in ("CH", "DE", "FR"):
        path = os.path.join(docs_dir, _PATH_DOC_FILE[code])
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        block = f"{_PATH_DOC_START}\n\n{_path_doc_section(code)}\n\n{_PATH_DOC_END}"
        if _PATH_DOC_START in text and _PATH_DOC_END in text:
            pre = text[:text.index(_PATH_DOC_START)]
            post = text[text.index(_PATH_DOC_END) + len(_PATH_DOC_END):]
            new = pre + block + post
        else:
            new = text.rstrip() + "\n\n" + block + "\n"
        if new != text:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(new)
            changed.append(_PATH_DOC_FILE[code])
    print("✓ path docs synced" + (": " + ", ".join(changed) if changed
                                   else " (already in sync)"))


# --- catalogue-coverage doc rendering ----------------------------------------
# A second auto-generated block (alongside path:auto) surfaces the honest coverage
# story in each country doc, from the SAME committed lock (data/coverage.lock.json)
# the player reads — single source of truth, so doc + player never diverge. The
# numbers come from src/validate.py (German catalogue as the measuring instrument).
_COV_DOC_START = ("<!-- coverage:auto:start — generated by `python run.py "
                  "coverage-docs`; do not edit by hand -->")
_COV_DOC_END = "<!-- coverage:auto:end -->"
_COV_BASE_LABEL = {
    "fr": {"cevni": "Code fluvial (CEVNI)", "colregs": "Code maritime (COLREGS/RIPAM)",
           "universal": "Matelotage universel"},
    "de": {"cevni": "Binnen (CEVNI)", "colregs": "See (KVR/COLREGS)",
           "universal": "Allgemeine Seemannschaft"},
}
_COV_TOPIC_LABEL = {       # principle slugs → readable topic names (doc `missing`)
    "fr": {"give-way": "priorité / route", "iala-buoyage": "balisage IALA",
           "nav-lights": "feux de navigation", "day-shapes": "marques de jour",
           "sound-signals": "signaux sonores", "waterway-signs": "panneaux de voie"},
    "de": {"give-way": "Vorfahrt", "iala-buoyage": "IALA-Betonnung",
           "nav-lights": "Lichterführung", "day-shapes": "Sichtzeichen",
           "sound-signals": "Schallsignale", "waterway-signs": "Schifffahrtszeichen"},
}
_COV_DOC_CHROME = {
    "fr": {
        "heading": "Couverture du catalogue : ce qui est mesuré (et ce qui ne l'est pas)",
        "intro": "Cette banque est **dérivée du droit**, pas du catalogue d'examen "
                 "officiel. Faute d'accès à la banque officielle, sa couverture est "
                 "mesurée *indirectement* : sur le tronc harmonisé (CEVNI/COLREGS), le "
                 "catalogue allemand officiel (ELWIS) sert d'instrument (`src/validate.py`). "
                 "Régénéré depuis `data/coverage.lock.json`{date}.",
        "cols": ["Base", "Couverture (de la part mesurable)",
                 "Part mesurable du catalogue officiel", "Sujets manquants"],
        "none": "—",
        "caveat": "**À lire honnêtement :** ces chiffres ne portent que sur la part "
                  "*étiquetée par sujet* du catalogue officiel (~la moitié) ; le reste "
                  "n'est pas mesuré. C'est un **plancher**, pas un signal « prêt pour "
                  "l'examen » — avant l'épreuve, faites un examen blanc à partir d'une "
                  "source officielle.",
        "official": "## Couverture du catalogue\n\nCes questions **sont** le catalogue "
                    "officiel ELWIS (§5(2) UrhG) — l'examen puise dans cette même banque. "
                    "Il n'y a donc pas de couverture à mesurer ici : le catalogue allemand "
                    "est l'instrument qui mesure les banques dérivées (CH/FR).",
        "verified": " (vérifié le {date})",
    },
    "de": {
        "heading": "Prüfungskatalog-Abdeckung: was gemessen ist (und was nicht)",
        "intro": "Diese Bank ist **aus dem Recht abgeleitet**, nicht aus dem amtlichen "
                 "Prüfungskatalog. Ohne Zugang zur amtlichen Bank wird die Abdeckung "
                 "*indirekt* gemessen: auf dem harmonisierten Kern (CEVNI/COLREGS) dient "
                 "der amtliche deutsche ELWIS-Katalog als Messlatte (`src/validate.py`). "
                 "Neu erzeugt aus `data/coverage.lock.json`{date}.",
        "cols": ["Basis", "Abdeckung (des messbaren Teils)",
                 "Messbarer Teil des amtlichen Katalogs", "Fehlende Themen"],
        "none": "—",
        "caveat": "**Ehrlich gelesen:** diese Zahlen betreffen nur den *themen-getaggten* "
                  "Teil des amtlichen Katalogs (~die Hälfte); der Rest ist ungemessen. Es "
                  "ist eine **Untergrenze**, kein „prüfungsbereit\"-Signal — mache vor der "
                  "Prüfung einen Probetest aus einer amtlichen Quelle.",
        "official": "## Prüfungskatalog-Abdeckung\n\nDiese Fragen **sind** der amtliche "
                    "ELWIS-Katalog (§5(2) UrhG) — die Prüfung schöpft aus derselben Bank. "
                    "Eine Abdeckung ist hier nicht zu messen: der deutsche Katalog ist die "
                    "Messlatte für die abgeleiteten Banken (CH/FR).",
        "verified": " (geprüft am {date})",
    },
}
_COV_DOC_DERIVED = {"CH", "FR"}        # banks scored; DE is the official yardstick


def _coverage_doc_section(code: str) -> str:
    """Render one country's catalogue-coverage block in its doc language, from the
    committed lock (`data/coverage.lock.json`) — the same numbers the player reads.
    DE gets the 'this IS the official catalogue' note; CH/FR get the measured table
    plus the honest floor caveat."""
    from src import validate
    lang = _PATH_DOC_LANG[code]
    ch = _COV_DOC_CHROME[lang]
    lock = validate.load_lock()
    gen = lock.get("generated") or ""
    if code not in _COV_DOC_DERIVED:
        return ch["official"]
    date_clause = ch["verified"].replace("{date}", gen) if gen else ""
    base_label = _COV_BASE_LABEL[lang]
    topic_label = _COV_TOPIC_LABEL[lang]
    tracks = (lock.get("banks", {}).get(code, {}) or {}).get("tracks", {})
    lines = [f"## {ch['heading']}", "",
             ch["intro"].replace("{date}", date_clause), "",
             "| " + " | ".join(ch["cols"]) + " |",
             "|" + "|".join(["---"] * len(ch["cols"])) + "|"]
    for base in scope_BASES_order():
        t = tracks.get(base)
        if not t:
            continue
        slice_pct = t.get("instrumented_pct")
        miss = ", ".join(topic_label.get(m, m) for m in t.get("missing", [])) or ch["none"]
        row = [base_label.get(base, base), f"{t['pct']} %",
               f"{slice_pct} %" if slice_pct is not None else ch["none"], miss]
        lines.append("| " + " | ".join(row) + " |")
    lines += ["", ch["caveat"]]
    return "\n".join(lines)


def scope_BASES_order():
    """The harmonised bases in display order (re-exported so the doc renderer is
    not coupled to import timing of src.scope)."""
    from src import scope
    return scope.BASES


def cmd_coverage_docs(args):
    """Rewrite the catalogue-coverage block in each country doc from the committed
    lock. `--refresh` first recomputes the lock from the built banks (needs them
    built); without it, the docs are re-rendered from the committed lock so the run
    is deterministic and offline (what tests/test_coverage.py pins)."""
    from src import validate
    if args.refresh:
        gen = _dt.date.today().isoformat()
        summ = validate.write_lock(generated=gen)
        n = sum(len(b.get("tracks", {})) for b in summ.get("banks", {}).values())
        print(f"✓ coverage lock refreshed: {validate.LOCK_PATH} "
              f"({len(summ.get('banks', {}))} banks, {n} tracks, {gen})")
    docs_dir = os.path.join(os.path.dirname(__file__), "docs")
    changed = []
    for code in ("CH", "DE", "FR"):
        path = os.path.join(docs_dir, _PATH_DOC_FILE[code])
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        block = f"{_COV_DOC_START}\n\n{_coverage_doc_section(code)}\n\n{_COV_DOC_END}"
        if _COV_DOC_START in text and _COV_DOC_END in text:
            pre = text[:text.index(_COV_DOC_START)]
            post = text[text.index(_COV_DOC_END) + len(_COV_DOC_END):]
            new = pre + block + post
        else:
            new = text.rstrip() + "\n\n" + block + "\n"
        if new != text:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(new)
            changed.append(_PATH_DOC_FILE[code])
    print("✓ coverage docs synced" + (": " + ", ".join(changed) if changed
                                       else " (already in sync)"))


def cmd_check_sources(args):
    """Diff live upstream sources against data/sources.lock.json and report drift.
    Exits non-zero on a law-grade change so a scheduled CI job can fail loudly."""
    from src import staleness
    changes, significant = staleness.check(
        refresh=not args.offline, update=args.update)
    print(staleness.format_report(changes))
    if args.update:
        print(f"\nLock re-blessed → {os.path.relpath(staleness.LOCK_PATH)}")
        return
    if significant:
        sys.exit(1)


def cmd_concepts(args):
    """Tag every question bank with its generative `principle` — the join key for
    the "why" concept cards (roadmap group A/D1). Deterministic + idempotent; the
    web bundlers run this too, so this command is for inspecting coverage or
    refreshing tags (incl. the France banks) without a full rebundle."""
    import glob
    from src.questions import schema as qschema
    from src.questions import principles as principlesmod
    total = tagged = 0
    by: dict[str, int] = {}
    for qdb in sorted(glob.glob(os.path.join(DATA, "questions.*.sqlite"))):
        conn = qschema.connect(qdb)
        st = principlesmod.tag_questions(conn, overwrite=args.overwrite)
        conn.close()
        total += st["total"]; tagged += st["tagged"]
        for k, v in st["by_principle"].items():
            by[k] = by.get(k, 0) + v
        print(f"  {os.path.basename(qdb)}: +{st['tagged']} tagged / {st['total']}")
    print(f"principle coverage: {tagged} newly tagged across {total} questions")
    for k, v in sorted(by.items()):
        print(f"  {v:5d}  {k}")
    print("  rebundle to ship tags: python run.py web   (and python run.py fr)")


def main():
    ap = argparse.ArgumentParser(description="Boating-licence pipeline")
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
    r.add_argument("--country", default=countries.DEFAULT, choices=countries.codes(),
                   help=f"country bank to review (default {countries.DEFAULT})")
    r.add_argument("--list", action="store_true", help="list pending drafts")
    r.add_argument("--theme", help="filter the listing to one theme")
    r.add_argument("--approve", nargs="+", metavar="ID", help="approve question id(s)")
    r.add_argument("--reject", nargs="+", metavar="ID", help="reject question id(s)")

    sub.add_parser("web", help="bundle the bank into the static web/ player")
    cc = sub.add_parser("concepts",
                        help="tag banks with their generative principle (the 'why' join key)")
    cc.add_argument("--overwrite", action="store_true",
                    help="re-tag even questions that already carry a principle")
    sub.add_parser("fr", help="build the France permis plaisance banks + web/fr/ "
                              "players (seed-driven; see docs/france.md)")
    sub.add_parser("path-docs", help="regenerate the path-to-permit section of the "
                                     "country docs from Country.path (single source)")
    cvd = sub.add_parser("coverage-docs",
                         help="sync the catalogue-coverage block in country docs from "
                              "data/coverage.lock.json (same source as the player)")
    cvd.add_argument("--refresh", action="store_true",
                     help="recompute the lock from the built banks first (needs them built)")
    cs = sub.add_parser("check-sources", help="diff live upstream law/catalogues "
                                              "against data/sources.lock.json")
    cs.add_argument("--offline", action="store_true",
                    help="hash the on-disk raw cache only (skip the network re-fetch)")
    cs.add_argument("--update", action="store_true",
                    help="re-bless: rewrite the lock to the current upstream state")
    v = sub.add_parser("validate", help="cross-check the derived CH/FR core against "
                                        "the official German catalogue (shared scope)")
    v.add_argument("--deep", action="store_true",
                   help="LLM divergence flagger (costs tokens); default is "
                        "deterministic coverage")
    v.add_argument("--bank", default="CH", choices=["CH", "FR"],
                   help="which derived bank to flag against DE (--deep only)")
    v.add_argument("--base", default="cevni", choices=["universal", "cevni", "colregs"],
                   help="harmonised base to compare (--deep only)")
    v.add_argument("--limit", type=int, default=20,
                   help="max derived questions to adjudicate (--deep only)")
    v.add_argument("--dry-run", action="store_true",
                   help="print the prompts that would be sent; no API call (--deep)")
    args = ap.parse_args()
    {"fetch": cmd_fetch, "parse": cmd_parse, "build": cmd_build,
     "questions": cmd_questions, "draft": cmd_draft, "review": cmd_review,
     "web": cmd_web, "fr": cmd_fr, "path-docs": cmd_path_docs,
     "coverage-docs": cmd_coverage_docs, "check-sources": cmd_check_sources,
     "validate": cmd_validate, "concepts": cmd_concepts}[args.cmd](args)


if __name__ == "__main__":
    main()
