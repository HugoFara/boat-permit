"""Build the French *permis plaisance* banks and bundle the static players.

France doesn't use the Swiss Fedlex pipeline (fetch → parse → normalize): its
content is the hand-authored, fully-cited seed bank in `seed_fr.py`. This module
turns those seeds into the canonical `Question` schema, writes one SQLite bank per
permit option (so the existing Anki/GIFT exporters can be reused unchanged), and
bundles a self-contained static player per option under `web/fr/<option>/`, plus a
France landing page at `web/fr/`.

Each option's player reuses the shared `web/app.js` / `web/i18n.js` / `web/style.css`
via `../../` — only the data (questions, manifest, downloads) and the per-option
chrome (stamped into the bank meta) differ.
"""

from __future__ import annotations

import datetime as _dt
import json
import os

from ..questions import schema as qschema
from ..questions.schema import Question, Choice, Provenance, make_question_id, validate
from .. import scope
from . import sources_fr, exam_fr, themes_fr
from .seed_fr import SEED

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
WEB_DIR = os.path.join(ROOT, "web")
FR_WEB = os.path.join(WEB_DIR, "fr")

LANGS = ("fr", "en")          # FR authoritative, EN unofficial study aid
DEFAULT_LANG = "fr"

# Theme → question kind (must be one of schema.KINDS). Météo/marée maps to the
# meteo kind; everything else is a rule-style MC.
_KIND_BY_THEME = {"meteo_maree": "meteo_mc"}


def _kind(theme: str) -> str:
    return _KIND_BY_THEME.get(theme, "rule_mc")


def _question(entry: dict, lang: str, idx: int) -> Question:
    """Build one Question (in `lang`) from a seed entry, with inline provenance."""
    src = sources_fr.get(entry["source"])
    loc = entry[lang]
    choices = [Choice(text=c[lang], is_correct=bool(c["correct"]))
               for c in entry["choices"]]
    # Stable id keyed on the source ref + the FR stem (so EN/FR variants of the
    # same item share a stem-derived suffix but differ by lang in the variant tag).
    unit_key = f"fr-{entry['source']}-{idx}"
    return Question(
        id=make_question_id(unit_key, entry["fr"]["stem"], f"{lang}"),
        theme=entry["theme"], kind=_kind(entry["theme"]),
        stem=loc["stem"], choices=choices, lang=lang,
        polarity=entry.get("polarity", "affirmative"), points=1,
        explanation=loc.get("explanation", ""),
        # Hand-authored and source-cited: approved so the public player serves them
        # (the France seed file is itself the durable, version-controlled record).
        review_status="approved", distractor_strategy="curated",
        generator="seed:fr.v1",
        provenance=Provenance(
            unit_id=unit_key, ref=entry["ref"], source=src.name, url=src.url,
            as_of=src.as_of, licence=src.licence))


def build_questions() -> dict[str, dict[str, list[Question]]]:
    """All France questions, grouped by option then language. Validates each and
    raises on the first invalid one (a bad seed never half-lands)."""
    out: dict[str, dict[str, list[Question]]] = {
        opt: {lg: [] for lg in LANGS} for opt in exam_fr.PROFILES}
    for i, entry in enumerate(SEED):
        opt = entry["option"]
        if opt not in out:
            raise ValueError(f"seed {i}: unknown option {opt!r}")
        if not themes_fr.is_valid(entry["theme"]):
            raise ValueError(f"seed {i}: unknown FR theme {entry['theme']!r}")
        if entry["theme"] not in themes_fr.OPTION_THEMES[opt]:
            raise ValueError(f"seed {i}: theme {entry['theme']!r} not in option {opt!r}")
        for lg in LANGS:
            q = _question(entry, lg, i)
            problems = validate(q)
            if problems:
                raise ValueError(f"seed {i} ({lg}): {'; '.join(problems)}")
            out[opt][lg].append(q)
    return out


# --- per-option chrome (stamped into bank meta; the player reads ui_* keys) ----
def _chrome(option: str) -> dict[str, dict[str, str]]:
    """Per-language UI chrome for one option (title/subtitle/banner/etc.). The
    player falls back to its built-in (Swiss) strings when these meta keys are
    absent, so this is what makes a France page read as France."""
    src_note_fr = ("Source : droit français (acte officiel, librement réutilisable "
                   "sous Licence Ouverte / Etalab) — RIPAM, RGP, arrêté du 28 "
                   "septembre 2007, Division 240. Aucune question issue d'une banque "
                   "d'opérateur.")
    src_note_en = ("Source: French law (official act, freely reusable under the "
                   "Open Licence / Etalab) — RIPAM, RGP, the 28 September 2007 order, "
                   "Division 240. No question taken from an operator's bank.")
    multi_fr = "Une seule réponse est correcte."
    multi_en = "Only one answer is correct."
    if option == "cotiere":
        return {
            "fr": {"ui_title": "Permis plaisance — option côtière (entraînement)",
                   "ui_h1": "Permis plaisance — option côtière",
                   "ui_subtitle": "Examen théorique · navigation maritime jusqu'à 6 milles d'un abri",
                   "ui_demo": "<strong>Banque d'entraînement complète (40 questions, "
                   "le format de l'examen).</strong> Questions dérivées du droit "
                   "français librement réutilisable (RIPAM, balisage IALA région A, "
                   "Division 240, arrêté du 28 sept. 2007). Ce n'est pas un examen "
                   "officiel.",
                   "ui_sourcenote": src_note_fr, "ui_multihint": multi_fr},
            "en": {"ui_title": "French boating licence — coastal option (practice)",
                   "ui_h1": "French boating licence — coastal option",
                   "ui_subtitle": "Theory exam · sea navigation up to 6 miles from a shelter",
                   "ui_demo": "<strong>Full practice bank (40 questions, the exam "
                   "format).</strong> Questions derived from freely-reusable French law "
                   "(RIPAM, IALA region A buoyage, Division 240, the 28 Sept. 2007 "
                   "order). Not an official exam.",
                   "ui_sourcenote": src_note_en, "ui_multihint": multi_en}}
    return {
        "fr": {"ui_title": "Permis plaisance — option eaux intérieures (entraînement)",
               "ui_h1": "Permis plaisance — option eaux intérieures",
               "ui_subtitle": "Examen théorique · rivières, canaux et lacs",
               "ui_demo": "<strong>Banque d'entraînement complète (40 questions, "
               "le format de l'examen).</strong> Questions dérivées du droit français "
               "librement réutilisable (règlement général de police de la navigation "
               "intérieure, arrêté du 28 sept. 2007). Ce n'est pas un examen officiel.",
               "ui_sourcenote": src_note_fr, "ui_multihint": multi_fr},
        "en": {"ui_title": "French boating licence — inland-waters option (practice)",
               "ui_h1": "French boating licence — inland-waters option",
               "ui_subtitle": "Theory exam · rivers, canals and lakes",
               "ui_demo": "<strong>Full practice bank (40 questions, the exam "
               "format).</strong> Questions derived from freely-reusable French law "
               "(the inland-navigation police regulation, the 28 Sept. 2007 order). "
               "Not an official exam.",
               "ui_sourcenote": src_note_en, "ui_multihint": multi_en}}


def _bank_json(questions: list[Question], cfg, chrome_lang: dict, lang: str,
               generated: str) -> dict:
    """Assemble one per-language bank file (meta + questions) in the player's shape."""
    from dataclasses import asdict
    qs = []
    for q in questions:
        d = asdict(q)
        d["correct"] = q.correct
        qs.append(d)
    meta = {
        "exam_questions": cfg.questions, "total_points": cfg.total_points,
        "points_per_question": cfg.points_per_question, "pass_points": cfg.pass_points,
        "time_limit_min": cfg.time_limit_min, "scoring": cfg.scoring,
        "canton": cfg.canton_default, "canton_code": cfg.canton_code,
        "permis": cfg.permis, "permis_label": cfg.label,
        "country": "FR", "generated": generated, "kb_version": "",
        "lang": lang, "unofficial": "true" if lang != "fr" else "false",
        **chrome_lang,
    }
    return {"meta": meta, "questions": qs}


# --- harmonised core (the portable, cross-country subset) ----------------------
def _core_bundles(out_dir: str, by_lang: dict[str, list[Question]], cfg,
                  chrome: dict[str, dict], generated: str) -> dict:
    """Write this option's per-base core sub-bundles and return the manifest `core`
    block (`{base: {lang: {path, count}}}`).

    France is seed-driven and self-contained, so — unlike the Swiss/German banks,
    which `run.py cmd_web` classifies into one shared global core — France emits its
    *own* per-base bundles here, alongside the national bank. The player (web/app.js)
    reads the `core` block identically and offers the National ⟷ Common core toggle;
    France's core is just France-local. Scope is derived (src/scope.py), never stored,
    so the national `questions.<lang>.json` written above stay byte-identical."""
    core: dict[str, dict] = {}
    for base in scope.BASES:
        per: dict[str, dict] = {}
        for lg, qs in by_lang.items():
            sub = [q for q in qs if scope.classify(q) == base]
            if not sub:
                continue
            path = f"questions.{base}.{lg}.json"
            payload = _bank_json(sub, cfg, chrome[lg], lg, generated)
            payload["meta"]["pool"] = base
            _write(os.path.join(out_dir, path),
                   json.dumps(payload, ensure_ascii=False, indent=2))
            per[lg] = {"path": path, "count": len(sub)}
        if per:
            core[base] = per
    return core


# --- web bundling --------------------------------------------------------------
def _write(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def _player_html(asset_prefix: str, nav: str, title: str) -> str:
    """A player page reusing the shared app via `asset_prefix` (e.g. '../../').
    Mirrors web/index.html's DOM so app.js/i18n.js drive it unchanged."""
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <link rel="stylesheet" href="{asset_prefix}style.css">
</head>
<body>
<nav class="countrybar">{nav}</nav>
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
<script src="{asset_prefix}i18n.js"></script>
<script src="{asset_prefix}app.js"></script>
</body>
</html>
"""


def _landing_html() -> str:
    """France landing page: choose an option. Static, no app.js."""
    return """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Permis plaisance France — entraînement</title>
  <link rel="stylesheet" href="../style.css">
</head>
<body>
<nav class="countrybar"><a href="../">🇨🇭 Suisse</a> · <span class="on">🇫🇷 France</span> · <a href="../de/">🇩🇪 Deutschland</a></nav>
<main id="app">
  <section class="screen">
    <h1>Permis plaisance — France</h1>
    <p class="sub">Outil d'étude libre · questions dérivées du droit français
      (RIPAM, RGP, arrêté du 28 septembre 2007), librement réutilisable.</p>
    <div class="banner"><strong>Choisissez votre option.</strong> L'examen théorique
      comporte 40 questions (5 fautes maximum). Ce n'est pas un examen officiel.</div>
    <div class="actions">
      <a class="dlbtn" href="cotiere/">Option côtière (mer, ≤ 6 milles)</a>
      <a class="dlbtn ghost" href="eaux_interieures/">Option eaux intérieures (rivières, canaux, lacs)</a>
    </div>
    <p class="fine">Les extensions « hauturière » (au large) et « grande plaisance
      eaux intérieures » (bateaux &gt; 20 m) existent aussi ; la hauturière repose
      sur une épreuve de carte et non un QCM, et n'est pas proposée ici.</p>
  </section>
</main>
<footer class="sitefoot">Outil d'étude libre · construit à partir de sources juridiques primaires</footer>
</body>
</html>
"""


def _nav(option: str) -> str:
    """Top country/option nav for an option player (at web/fr/<option>/)."""
    opts = [("cotiere", "Côtière"), ("eaux_interieures", "Eaux intérieures")]
    links = []
    for code, label in opts:
        if code == option:
            links.append(f'<span class="on">{label}</span>')
        else:
            links.append(f'<a href="../{code}/">{label}</a>')
    return ('<a href="../../">🇨🇭 Suisse</a> · <a href="../">🇫🇷 France</a> · '
            '<a href="../../de/">🇩🇪 Deutschland</a> · ' + " · ".join(links))


def build() -> dict:
    """Build both option banks and bundle web/fr/. Returns a small stats dict."""
    import shutil
    from tools import anki, gift

    by_option = build_questions()
    generated = _dt.date.today().isoformat()
    stats: dict = {"options": {}, "generated": generated}

    # France landing page (the country registry — src/countries/ — owns the
    # cross-country metadata; this build just emits the self-contained web/fr/
    # players, cross-linked to the Swiss root via the country switcher).
    _write(os.path.join(FR_WEB, "index.html"), _landing_html())

    for option, by_lang in by_option.items():
        cfg = exam_fr.profile(option)
        chrome = _chrome(option)
        out_dir = os.path.join(FR_WEB, option)
        # Fresh per-option bank DB (only this option's questions, both languages),
        # so the Anki/GIFT exporters produce option-scoped decks.
        db_path = os.path.join(DATA_DIR, f"questions.fr_{option}.sqlite")
        if os.path.exists(db_path):
            os.remove(db_path)
        conn = qschema.connect(db_path)
        all_q = [q for lg in LANGS for q in by_lang[lg]]
        qschema.write_questions(conn, all_q)

        # Per-language bank JSON (player-shaped, with per-lang chrome in meta).
        langs_present = [lg for lg in LANGS if by_lang[lg]]
        for lg in langs_present:
            payload = _bank_json(by_lang[lg], cfg, chrome[lg], lg, generated)
            _write(os.path.join(out_dir, f"questions.{lg}.json"),
                   json.dumps(payload, ensure_ascii=False, indent=2))
        # Canonical fallback file (FR), matching the player's fetch chain.
        _write(os.path.join(out_dir, "questions.json"),
               json.dumps(_bank_json(by_lang["fr"], cfg, chrome["fr"], "fr", generated),
                          ensure_ascii=False, indent=2))

        # Offline-study downloads (Anki + GIFT), one set per language.
        anki_dir, gift_dir = os.path.join(out_dir, "anki"), os.path.join(out_dir, "gift")
        for d in (anki_dir, gift_dir):
            if os.path.exists(d):
                shutil.rmtree(d)
        anki_avail, gift_avail = {}, {}
        for lg in langs_present:
            n, n_img = anki.export_to(conn, anki_dir, lg)
            if n:
                anki_avail[lg] = {"apkg": f"anki/boat-permit.{lg}.apkg",
                                  "tsv": f"anki/boat-permit.{lg}.tsv",
                                  "count": n, "images": n_img}
            ng = gift.export_to(conn, gift_dir, lg)
            if ng:
                gift_avail[lg] = {"gift": f"gift/boat-permit.{lg}.gift", "count": ng}
        conn.close()

        # Harmonised-core sub-bundles (universal/cevni/colregs), classified by
        # src/scope.py. France-local (see _core_bundles): they light up the player's
        # National ⟷ Common core toggle so a learner can drill just the portable
        # subset (RIPAM/IALA at sea, the inland code on rivers) without the French
        # permit/equipment statute.
        core = _core_bundles(out_dir, {lg: by_lang[lg] for lg in langs_present},
                             cfg, chrome, generated)

        # Manifest: no `cantons` key → the player hides its region picker (the French
        # exam is national). `supported` is fr/en only → langbar shows just those.
        manifest = {
            "default": DEFAULT_LANG, "supported": list(langs_present),
            "available": {lg: {"count": len(by_lang[lg]),
                               "unofficial": lg != "fr"} for lg in langs_present},
            "country": "FR", "option": option,
            "core": core,
            "anki": anki_avail, "gift": gift_avail,
        }
        _write(os.path.join(out_dir, "languages.json"),
               json.dumps(manifest, ensure_ascii=False, indent=2))

        # The option's player page (reuses ../../app.js etc.).
        _write(os.path.join(out_dir, "index.html"),
               _player_html("../../", _nav(option), chrome["fr"]["ui_title"]))

        stats["options"][option] = {
            "questions_fr": len(by_lang["fr"]), "questions_en": len(by_lang["en"]),
            "anki": sorted(anki_avail), "gift": sorted(gift_avail),
            "themes": sorted({q.theme for q in by_lang["fr"]}),
            # FR-language core counts per base (the portable subset offered by the
            # National ⟷ Common core toggle); national/local stay out of the core.
            "core": {b: core[b]["fr"]["count"] for b in scope.BASES
                     if core.get(b, {}).get("fr")}}
    return stats
