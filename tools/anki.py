"""Export the boat-permit bank to Anki, and import edits back (round-trip).

Two interchange formats, one mapping:

  * **.apkg** — a real Anki package: a zip holding a SQLite collection plus the
    figure images, built with the standard library only (zipfile + sqlite3). Drop
    it into Anki / AnkiMobile / AnkiDroid and study with spaced repetition. Cards
    are filed into one **subdeck per theme** ("Permis bateau · Léman (FR)::
    Signalisation", …) so domain-by-domain study works in Anki out of the box.
  * **.tsv** — a flat, human-editable table (one row per question, correct
    options named in their own column). This is the round-trip channel: edit it
    in a spreadsheet, then `import` to fold the changes back into the bank as
    *pending* drafts (so they pass the review gate again before publication).

Why this guides the schema toward an SRS app: an Anki note is
(guid, fields, tags, media). Mapping a Question onto it forces the bank to expose
a stable per-question identity (we already have `Question.id` → the note GUID),
a clean front/back split, theme/lang/kind as tags, and provenance on the card —
exactly what a spaced-repetition client needs. The mapping is lossless for the
fields a learner edits (stem, choice texts, explanation); answer *structure*
(which options are correct, the image, provenance) stays owned by the bank, so a
careless edit can never silently flip an answer — on import an edited question is
structure-locked to its original exactly as the EN translation pipeline does.

Stages:
  export [lang] [--tsv] [--apkg]   -> data/anki/boat-permit[.lang].{apkg,tsv}
  import <file.tsv|.apkg> [--apply]   diff vs the bank; --apply writes
                                       new/edited notes as pending drafts

All ids in the package are derived deterministically from content (sha1), so a
rebuild is byte-identical — no timestamps, no randomness.
"""

from __future__ import annotations

import csv
import html
import json
import os
import re
import sqlite3
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import themes                                  # noqa: E402
from src.questions import schema as qschema             # noqa: E402
from src.questions.schema import Question, Choice, Provenance, make_question_id  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
# The Anki/GIFT exports bundle the Swiss bank that still backs the web/ root.
QDB_PATH = os.path.join(DATA, "questions.ch.sqlite")
OUT_DIR = os.path.join(DATA, "anki")

# Fixed collection timestamps — deterministic builds (Anki remaps on import).
_CRT = 1700000000          # collection "created" epoch seconds
_NOW_MS = 1700000000000    # mod / schema-mod, ms

# Localised card chrome (labels only — question text is the bank's).
_L = {
    "fr": {"deck": "Permis bateau · Léman", "answer": "Réponse", "source": "Source",
           "asof": "état {d}"},
    "de": {"deck": "Bootsprüfung · Genfersee", "answer": "Antwort", "source": "Quelle",
           "asof": "Stand {d}"},
    "it": {"deck": "Licenza nautica · Lemano", "answer": "Risposta", "source": "Fonte",
           "asof": "stato {d}"},
    "en": {"deck": "Boat permit · Lake Geneva", "answer": "Answer", "source": "Source",
           "asof": "as of {d}"},
}
_THEME_LABELS = {
    "fr": {"definitions": "Définitions", "meteorologie": "Météorologie",
           "lois": "Lois sur la navigation", "signalisation": "Signalisation",
           "matelotage": "Matelotage", "eaux_frontalieres": "Eaux frontalières",
           "voile": "Navigation à voile"},
    "de": {"definitions": "Begriffe", "meteorologie": "Meteorologie",
           "lois": "Schifffahrtsrecht", "signalisation": "Signale",
           "matelotage": "Seemannschaft", "eaux_frontalieres": "Grenzgewässer",
           "voile": "Segeln"},
    "it": {"definitions": "Definizioni", "meteorologie": "Meteorologia",
           "lois": "Norme di navigazione", "signalisation": "Segnaletica",
           "matelotage": "Marineria", "eaux_frontalieres": "Acque di confine",
           "voile": "Navigazione a vela"},
    "en": {"definitions": "Definitions", "meteorologie": "Meteorology",
           "lois": "Navigation law", "signalisation": "Signs",
           "matelotage": "Seamanship", "eaux_frontalieres": "Border waters",
           "voile": "Sailing"},
}


def _theme_label(lang: str, theme: str) -> str:
    # Swiss themes have localized labels here; other countries' themes (FR/DE) fall
    # back to the shared theme registry, then to the raw id.
    local = _THEME_LABELS.get(lang, _THEME_LABELS["fr"]).get(theme)
    return local or themes.label(theme)


# --- deterministic 63-bit ids from a name (no timestamps / randomness) ---------
def _sid(name: str) -> int:
    import hashlib
    return int(hashlib.sha1(name.encode()).hexdigest()[:15], 16)  # <2^60, positive


def _csum(first_field: str) -> int:
    import hashlib
    return int(hashlib.sha1(first_field.encode("utf-8")).hexdigest()[:8], 16)


def _media_name(path: str) -> str:
    """Flatten a data/-relative asset path to a collision-free media filename:
    data/assets/oni/de/image115.png -> oni_de_image115.png."""
    rel = path[len("data/assets/"):] if path.startswith("data/assets/") else path
    return rel.replace("/", "_").replace("\\", "_")


CHOICE_LETTERS = "ABCDEFGH"


# === the Anki note model =======================================================
MODEL_ID = _sid("boat-permit::model::mc.v1")
FIELDS = ["Id", "Stem", "Image", "Choices", "Answer", "Explanation", "Source"]

_QFMT = ('<div class="stem">{{Stem}}</div>\n{{Image}}\n'
         '<div class="choices">{{Choices}}</div>')
_AFMT = ('{{FrontSide}}\n<hr id="answer">\n<div class="answer">{{Answer}}</div>\n'
         '{{#Explanation}}<div class="explain">{{Explanation}}</div>{{/Explanation}}\n'
         '<div class="source">{{Source}}</div>')
_CSS = (".card{font-family:Arial,Helvetica,sans-serif;font-size:18px;color:#1b2733;"
        "background:#fff;text-align:left;max-width:40em;margin:0 auto;line-height:1.45}"
        ".stem{font-weight:600;margin-bottom:.6em}"
        ".choices{white-space:pre-line;margin:.4em 0}"
        ".answer{font-weight:600;color:#0a7d33;margin:.4em 0}"
        ".explain{margin:.5em 0;color:#33424f}"
        ".source{font-size:.8em;color:#6b7785;margin-top:.6em}"
        "img{max-width:100%;max-height:300px;display:block;margin:.5em 0}"
        "hr#answer{border:none;border-top:1px solid #d4dbe2;margin:.8em 0}")


def _model_def(default_did: int) -> dict:
    return {
        "id": MODEL_ID, "name": "BoatPermit MC", "type": 0, "mod": 0, "usn": 0,
        "sortf": 0, "did": default_did, "latexPre": "", "latexPost": "", "vers": [],
        "tags": [], "css": _CSS,
        "tmpls": [{"name": "Card 1", "ord": 0, "qfmt": _QFMT, "afmt": _AFMT,
                   "did": None, "bqfmt": "", "bafmt": ""}],
        "flds": [{"name": n, "ord": i, "sticky": False, "rtl": False,
                  "font": "Arial", "size": 20, "media": []}
                 for i, n in enumerate(FIELDS)],
        "req": [[0, "any", [1]]],            # template 0 needs the Stem field
    }


# === collection JSON blobs (Anki schema 11 defaults) ===========================
_CONF = {"activeDecks": [1], "addToCur": True, "collapseTime": 1200, "curDeck": 1,
         "curModel": str(MODEL_ID), "dueCounts": True, "estTimes": True,
         "newBury": True, "newSpread": 0, "nextPos": 1, "sortBackwards": False,
         "sortType": "noteFld", "timeLim": 0}
_DCONF = {"1": {"id": 1, "name": "Default", "mod": 0, "usn": 0, "maxTaken": 60,
                "autoplay": True, "timer": 0, "replayq": True,
                "new": {"bury": False, "delays": [1, 10], "initialFactor": 2500,
                        "ints": [1, 4, 0], "order": 1, "perDay": 20, "separate": True},
                "rev": {"bury": False, "ease4": 1.3, "fuzz": 0.05, "ivlFct": 1,
                        "maxIvl": 36500, "minSpace": 1, "perDay": 200, "hardFactor": 1.2},
                "lapse": {"delays": [10], "leechAction": 1, "leechFails": 8,
                          "minInt": 1, "mult": 0}}}


def _deck_entry(did: int, name: str) -> dict:
    return {"id": did, "name": name, "desc": "", "mod": 0, "usn": 0, "collapsed": False,
            "dyn": 0, "conf": 1, "extendNew": 10, "extendRev": 50,
            "newToday": [0, 0], "revToday": [0, 0], "lrnToday": [0, 0],
            "timeToday": [0, 0]}


_DDL = """
CREATE TABLE col (id integer primary key, crt integer not null, mod integer not null,
  scm integer not null, ver integer not null, dty integer not null, usn integer not null,
  ls integer not null, conf text not null, models text not null, decks text not null,
  dconf text not null, tags text not null);
CREATE TABLE notes (id integer primary key, guid text not null, mid integer not null,
  mod integer not null, usn integer not null, tags text not null, flds text not null,
  sfld integer not null, csum integer not null, flags integer not null, data text not null);
CREATE TABLE cards (id integer primary key, nid integer not null, did integer not null,
  ord integer not null, mod integer not null, usn integer not null, type integer not null,
  queue integer not null, due integer not null, ivl integer not null, factor integer not null,
  reps integer not null, lapses integer not null, left integer not null, odue integer not null,
  odid integer not null, flags integer not null, data text not null);
CREATE TABLE revlog (id integer primary key, cid integer not null, usn integer not null,
  ease integer not null, ivl integer not null, lastIvl integer not null, factor integer not null,
  time integer not null, type integer not null);
CREATE TABLE graves (usn integer not null, oid integer not null, type integer not null);
CREATE INDEX ix_notes_usn on notes (usn);
CREATE INDEX ix_cards_usn on cards (usn);
CREATE INDEX ix_revlog_usn on revlog (usn);
CREATE INDEX ix_cards_nid on cards (nid);
CREATE INDEX ix_cards_sched on cards (did, queue, due);
CREATE INDEX ix_revlog_cid on revlog (cid);
CREATE INDEX ix_notes_csum on notes (csum);
"""


# === field rendering ===========================================================
def _render_fields(q: Question, lang: str) -> tuple[list[str], str | None]:
    """Return (the 7 note fields, media data-path or None)."""
    L = _L.get(lang, _L["fr"])
    media = q.image if q.image else None
    img = f'<img src="{_media_name(q.image)}">' if q.image else ""
    choices = "\n".join(f"{CHOICE_LETTERS[i]}. {html.escape(c.text)}"
                        for i, c in enumerate(q.choices))
    letters = [CHOICE_LETTERS[i] for i in q.correct]
    correct_txt = " / ".join(html.escape(q.choices[i].text) for i in q.correct
                             if q.choices[i].text)
    answer = f'{L["answer"]} : {", ".join(letters)}'
    if correct_txt:
        answer += f"<br>{correct_txt}"
    p = q.provenance
    ref = html.escape(p.ref or p.source or "")
    src = (f'<a href="{html.escape(p.url)}">{ref}</a>' if p.url else ref)
    if p.source and p.source != (p.ref or ""):
        src += f" — {html.escape(p.source)}"
    if p.as_of:
        src += f' ({L["asof"].format(d=html.escape(p.as_of))})'
    src = f'{L["source"]} : {src}'
    return [q.id, html.escape(q.stem), img, choices, answer,
            html.escape(q.explanation or ""), src], media


def _tags(q: Question) -> str:
    m = re.match(r"[a-z_]+", q.provenance.unit_id or "")   # leading source id
    src_id = m.group(0) if m else "kb"
    parts = [f"theme:{q.theme}", f"lang:{q.lang}", f"kind:{q.kind}", f"src:{src_id}"]
    return " " + " ".join(parts) + " "       # Anki convention: space-padded


# === apkg writer ===============================================================
def _build_apkg(questions: list[Question], lang: str, out_path: str) -> int:
    L = _L.get(lang, _L["fr"])
    top = f'{L["deck"]} ({lang.upper()})'
    # One subdeck per theme actually used, plus the (required) default deck id 1.
    # Order by the Swiss taxonomy where applicable; other countries' themes (FR/DE)
    # aren't in it, so they sort after, stably by id.
    _order = list(themes.THEMES)
    used_themes = sorted({q.theme for q in questions},
                         key=lambda t: (_order.index(t) if t in _order else len(_order), t))
    decks = {"1": _deck_entry(1, "Default")}
    theme_did: dict[str, int] = {}
    for th in used_themes:
        name = f"{top}::{_theme_label(lang, th)}"
        did = _sid(f"deck::{name}")
        theme_did[th] = did
        decks[str(did)] = _deck_entry(did, name)
    models = {str(MODEL_ID): _model_def(1)}

    tmp_db = out_path + ".tmp.anki2"
    if os.path.exists(tmp_db):
        os.remove(tmp_db)
    conn = sqlite3.connect(tmp_db)
    conn.executescript(_DDL)
    conn.execute(
        "INSERT INTO col VALUES (1,?,?,?,11,0,0,0,?,?,?,?,'{}')",
        (_CRT, _NOW_MS, _NOW_MS, json.dumps(_CONF), json.dumps(models),
         json.dumps(decks), json.dumps(_DCONF)))

    media: dict[str, str] = {}          # media-index -> flat filename
    media_src: dict[str, str] = {}      # flat filename -> abs source path
    used_ids: set[int] = set()

    def uniq(seed: str) -> int:
        i = _sid(seed)
        while i in used_ids:
            i += 1
        used_ids.add(i)
        return i

    for pos, q in enumerate(sorted(questions, key=lambda x: x.id)):
        flds, mpath = _render_fields(q, lang)
        if mpath:
            fname = _media_name(mpath)
            abs_src = os.path.join(BASE, mpath)
            if os.path.exists(abs_src) and fname not in media_src:
                media_src[fname] = abs_src
        nid = uniq("note::" + q.id)
        cid = uniq("card::" + q.id)
        conn.execute(
            "INSERT INTO notes VALUES (?,?,?,?,-1,?,?,?,?,0,'')",
            (nid, q.id, MODEL_ID, _CRT, _tags(q), "\x1f".join(flds),
             flds[0], _csum(flds[0])))
        conn.execute(
            "INSERT INTO cards VALUES (?,?,?,0,?,-1,0,0,?,0,0,0,0,0,0,0,0,'')",
            (cid, nid, theme_did[q.theme], _CRT, pos + 1))
    conn.commit()
    conn.close()

    # Assign media indices in a stable order, then zip everything up.
    for idx, fname in enumerate(sorted(media_src)):
        media[str(idx)] = fname
    if os.path.exists(out_path):
        os.remove(out_path)

    def _put(z, name, data):
        # Fixed timestamp so a rebuild is byte-identical (no file-mtime noise).
        zi = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
        zi.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(zi, data)

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        with open(tmp_db, "rb") as fh:
            _put(z, "collection.anki2", fh.read())
        _put(z, "media", json.dumps(media))
        for idx, fname in media.items():
            with open(media_src[fname], "rb") as fh:
                _put(z, idx, fh.read())
    os.remove(tmp_db)
    return len(media)


# === TSV writer / reader =======================================================
TSV_COLS = ["id", "lang", "theme", "kind", "polarity", "stem", "choices",
            "correct", "explanation", "source_ref", "source_url", "source_as_of",
            "image"]
_CHOICE_SEP = " | "


def _write_tsv(questions: list[Question], out_path: str) -> None:
    with open(out_path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(TSV_COLS)
        for q in sorted(questions, key=lambda x: (x.theme, x.id)):
            p = q.provenance
            w.writerow([
                q.id, q.lang, q.theme, q.kind, q.polarity, q.stem,
                _CHOICE_SEP.join(c.text for c in q.choices),
                ",".join(CHOICE_LETTERS[i] for i in q.correct),
                q.explanation or "", p.ref, p.url, p.as_of,
                q.image or ""])


def _read_tsv(path: str) -> list[dict]:
    out = []
    with open(path, encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            choices = [c.strip() for c in (row.get("choices") or "").split(_CHOICE_SEP)]
            choices = [c for c in choices if c]
            letters = [x.strip().upper() for x in (row.get("correct") or "").split(",")]
            correct = sorted(CHOICE_LETTERS.index(l) for l in letters
                             if l in CHOICE_LETTERS and CHOICE_LETTERS.index(l) < len(choices))
            out.append({
                "id": (row.get("id") or "").strip(), "lang": (row.get("lang") or "fr").strip(),
                "theme": (row.get("theme") or "").strip(), "kind": (row.get("kind") or "").strip(),
                "polarity": (row.get("polarity") or "affirmative").strip(),
                "stem": (row.get("stem") or "").strip(), "choices": choices,
                "correct": correct, "explanation": (row.get("explanation") or "").strip(),
                "source_ref": (row.get("source_ref") or "").strip(),
                "source_url": (row.get("source_url") or "").strip(),
                "source_as_of": (row.get("source_as_of") or "").strip(),
                "image": (row.get("image") or "").strip() or None})
    return out


def _read_apkg(path: str) -> list[dict]:
    """Best-effort read of an .apkg back into the same dict shape as _read_tsv.
    Parses the structured note fields (Stem/Choices/Answer) we wrote."""
    import tempfile
    out = []
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        col = "collection.anki2" if "collection.anki2" in names else "collection.anki21"
        with tempfile.NamedTemporaryFile(suffix=".anki2", delete=False) as tf:
            tf.write(z.read(col))
            tmp = tf.name
    try:
        conn = sqlite3.connect(tmp)
        for guid, tags, flds in conn.execute("SELECT guid, tags, flds FROM notes"):
            f = flds.split("\x1f")
            if len(f) < len(FIELDS):
                continue
            tagd = dict(t.split(":", 1) for t in tags.split() if ":" in t)
            choices, correct = [], []
            for line in f[3].split("\n"):
                m = re.match(r"\s*([A-H])\.\s*(.*)", line)
                if m:
                    choices.append(html.unescape(m.group(2).strip()))
            for m in re.finditer(r"\b([A-H])\b", f[4].split("<br>")[0]):
                idx = CHOICE_LETTERS.index(m.group(1))
                if idx < len(choices):
                    correct.append(idx)
            img = re.search(r'src="([^"]+)"', f[2])
            out.append({
                "id": html.unescape(f[0]), "lang": tagd.get("lang", "fr"),
                "theme": tagd.get("theme", ""), "kind": tagd.get("kind", ""),
                "polarity": "affirmative", "stem": html.unescape(f[1]),
                "choices": choices, "correct": sorted(set(correct)),
                "explanation": html.unescape(f[5]),
                "source_ref": "", "source_url": "", "source_as_of": "",
                "image": img.group(1) if img else None})
        conn.close()
    finally:
        os.remove(tmp)
    return out


# === commands ==================================================================
def _exportable(conn, lang: str | None) -> list[Question]:
    return [q for q in qschema.load_questions(conn)
            if q.review_status in qschema.EXPORTABLE_STATUSES
            and (lang is None or q.lang == lang)]


def export_to(conn, out_dir: str, lang: str | None) -> tuple[int, int]:
    """Build boat-permit[.lang].{apkg,tsv} into `out_dir` from an open bank
    connection. Used by `run.py web` so the static player can offer the deck as a
    download. Returns (n_questions, n_images)."""
    qs = _exportable(conn, lang)
    if not qs:
        return 0, 0
    os.makedirs(out_dir, exist_ok=True)
    sfx = "" if lang is None else f".{lang}"
    stem = os.path.join(out_dir, f"boat-permit{sfx}")
    n_media = _build_apkg(qs, lang or "fr", stem + ".apkg")
    _write_tsv(qs, stem + ".tsv")
    return len(qs), n_media


def cmd_export(args) -> None:
    if not os.path.exists(QDB_PATH):
        sys.exit("no question bank — run `python run.py questions` first")
    conn = qschema.connect(QDB_PATH)
    lang = args.lang
    want_tsv, want_apkg = args.tsv, args.apkg
    if not want_tsv and not want_apkg:           # default: both
        want_tsv = want_apkg = True
    os.makedirs(OUT_DIR, exist_ok=True)
    qs = _exportable(conn, lang)
    if not qs:
        sys.exit(f"no exportable questions for lang={lang!r}")
    sfx = "" if lang is None else f".{lang}"
    stem = os.path.join(OUT_DIR, f"boat-permit{sfx}")
    if want_apkg:
        n_media = _build_apkg(qs, lang or "fr", stem + ".apkg")
        print(f"✓ {stem}.apkg  ({len(qs)} notes, {n_media} images)")
    if want_tsv:
        _write_tsv(qs, stem + ".tsv")
        print(f"✓ {stem}.tsv  ({len(qs)} rows)")
    conn.close()


def _to_question(d: dict, orig: Question | None) -> tuple[Question | None, str]:
    """Build a Question from an imported row. If it matches a bank question
    (orig), structure-lock to the original (answer flags/image/provenance stay
    the bank's; only text is taken from the import). Returns (question, status)
    where status is 'new' | 'edited' | 'unchanged' | 'invalid:<why>'."""
    if orig is not None:
        # text-only edit, structure-locked (same contract as the EN translation)
        if len(d["choices"]) != len(orig.choices):
            return None, "invalid:choice count differs from bank original"
        same = (d["stem"] == orig.stem
                and [c.text for c in orig.choices] == d["choices"]
                and (d["explanation"] or "") == (orig.explanation or ""))
        if same:
            return None, "unchanged"
        choices = [Choice(text=d["choices"][i], image=orig.choices[i].image,
                          is_correct=orig.choices[i].is_correct)
                   for i in range(len(orig.choices))]
        q = Question(
            id=orig.id, theme=orig.theme, kind=orig.kind, stem=d["stem"],
            lang=orig.lang, choices=choices, polarity=orig.polarity,
            image=orig.image, points=orig.points, explanation=d["explanation"],
            review_status="pending", distractor_strategy=orig.distractor_strategy,
            generator="anki-import:edit", provenance=orig.provenance)
        return (q, "edited") if not qschema.validate(q) else \
            (None, "invalid:" + "; ".join(qschema.validate(q)))
    # brand-new question contributed via Anki/TSV — correctness comes from import
    if not d["choices"] or not d["correct"]:
        return None, "invalid:new question needs choices and a correct column"
    choices = [Choice(text=t, is_correct=(i in d["correct"]))
               for i, t in enumerate(d["choices"])]
    unit_id = f"anki-import:{d['id'] or make_question_id('anki', d['stem'])}"
    prov = Provenance(unit_id=unit_id, ref=d["source_ref"], source=d["source_ref"],
                      url=d["source_url"], as_of=d["source_as_of"],
                      licence="user-contributed")
    qid = d["id"] or make_question_id(unit_id, d["stem"], d["lang"])
    q = Question(
        id=qid, theme=d["theme"] or themes.tag_theme(text=d["stem"]),
        kind=d["kind"] or "rule_mc", stem=d["stem"], lang=d["lang"],
        choices=choices, polarity=d["polarity"] or "affirmative",
        image=d["image"], explanation=d["explanation"], review_status="pending",
        generator="anki-import:new", provenance=prov)
    probs = qschema.validate(q)
    return (q, "new") if not probs else (None, "invalid:" + "; ".join(probs))


def cmd_import(args) -> None:
    path = args.file
    if not os.path.exists(path):
        sys.exit(f"no such file: {path}")
    rows = _read_apkg(path) if path.endswith(".apkg") else _read_tsv(path)
    conn = qschema.connect(QDB_PATH)
    bank = {q.id: q for q in qschema.load_questions(conn)}
    buckets: dict[str, list] = {"new": [], "edited": [], "unchanged": [], "invalid": []}
    to_write = []
    for d in rows:
        q, status = _to_question(d, bank.get(d["id"]))
        key = status.split(":", 1)[0]
        buckets.setdefault(key, []).append((d["id"], status))
        if q is not None:
            to_write.append(q)
    print(f"read {len(rows)} rows from {os.path.basename(path)}:")
    for k in ("new", "edited", "unchanged", "invalid"):
        print(f"  {k:10} {len(buckets[k])}")
    for qid, status in buckets["invalid"][:20]:
        print(f"    ! {qid or '(no id)'}: {status[len('invalid:'):]}")
    if args.apply and to_write:
        qschema.write_questions(conn, to_write)
        print(f"→ wrote {len(to_write)} questions as pending (review before publishing).")
        print("  review queue:", qschema.counts_by_status(conn))
    elif to_write:
        print(f"(dry run — {len(to_write)} would be written. Re-run with --apply.)")
    conn.close()


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Anki export/import for the question bank")
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export", help="write data/anki/boat-permit[.lang].{apkg,tsv}")
    e.add_argument("lang", nargs="?", default=None,
                   help="content language to export (default: all, mixed bank)")
    e.add_argument("--tsv", action="store_true", help="write only the TSV")
    e.add_argument("--apkg", action="store_true", help="write only the .apkg")
    i = sub.add_parser("import", help="fold a .tsv/.apkg back into the bank (pending)")
    i.add_argument("file", help="path to a .tsv or .apkg produced/edited from the bank")
    i.add_argument("--apply", action="store_true",
                   help="actually write (default is a dry-run diff)")
    args = ap.parse_args()
    {"export": cmd_export, "import": cmd_import}[args.cmd](args)


if __name__ == "__main__":
    main()
