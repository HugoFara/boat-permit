"""Canonical question schema + SQLite/JSON store + scoring.

One record type, `Question`, covers every question kind (figure recognition, rule
MC, definition MC, …). Shape decisions are locked here so generators downstream
target a stable contract:

  * **Multi-select.** The real exam gives 3 options per question, of which *one or
    sometimes two* are correct. So answers are `correct: list[int]` (indices into
    `choices`), not a singular field. Figure-recognition questions are simply the
    length-1 case — no special shape.
  * **Point-based scoring.** 3 points/question, 180 total, pass at 165/180 (lose at
    most 15 *fault points*). The Vaud office equates 165 with "55/60 réponses
    correctes", which reads as all-or-nothing per question — but the exact
    partial-credit mechanic is undocumented, so `score()` is a pure, swappable
    function and the mode lives in `ExamConfig`, never hardcoded.
  * **Provenance + as-of.** Every question links to the KB unit it was derived from
    and carries that unit's `as_of` legal version, so a question can be flagged
    stale when the underlying ordinance is amended.
  * **Review gate.** `review_status` defaults to `pending`; only `auto_approved`
    (deterministic templates) or human-`approved` questions are export-eligible.
  * **Cantonal config.** Timer / thresholds are config, not constants (Vaud/Léman
    defaults: 60 q, 50 min, 165/180).
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field, asdict

from .. import themes

# --- controlled vocabularies (validation rejects anything outside these) -------
KINDS = {"figure_recognition", "rule_mc", "definition_mc", "meteo_mc",
         "matelotage_mc", "frontiere_mc"}
POLARITIES = {"affirmative", "negative"}           # negative = "lequel n'est PAS…"
REVIEW_STATUSES = {"auto_approved", "pending", "approved", "rejected"}
DISTRACTOR_STRATEGIES = {"sibling_random", "confusion_set", "curated", "n/a"}
# Only these may be published to the static (public) player:
EXPORTABLE_STATUSES = {"auto_approved", "approved"}


@dataclass
class Choice:
    text: str
    image: str | None = None      # repo-relative asset path, for figure options
    is_correct: bool = False


@dataclass
class Provenance:
    unit_id: str                  # the KB unit this question derives from
    ref: str                      # human ref, e.g. "ONI Annexe 2 – fig. 22"
    source: str                   # "ONI (RS 747.201.1)"
    url: str
    as_of: str = ""               # KB unit legal_version ("2022-01-01"); "" if n/a
    licence: str = ""


@dataclass
class Question:
    id: str
    theme: str                    # one of themes.THEMES (drives exam balancing)
    kind: str                     # one of KINDS
    stem: str
    choices: list[Choice]
    provenance: Provenance
    polarity: str = "affirmative"
    image: str | None = None      # the figure being asked about (figure questions)
    points: int = 3
    explanation: str = ""
    review_status: str = "pending"
    distractor_strategy: str = "n/a"
    generator: str = ""           # template id or model tag that produced it

    @property
    def correct(self) -> list[int]:
        """Indices of the correct choices (the multi-select answer)."""
        return [i for i, c in enumerate(self.choices) if c.is_correct]


@dataclass
class ExamConfig:
    """A cantonal exam profile. Defaults are Vaud/Léman, officially sourced."""
    questions: int = 60
    total_points: int = 180
    points_per_question: int = 3
    pass_points: int = 165
    time_limit_min: int = 50
    scoring: str = "all_or_nothing"   # | "partial"
    canton_default: str = "VD/Léman"


def make_question_id(unit_id: str, stem: str, variant: str = "") -> str:
    """Stable id: KB-unit prefix + short hash of (unit, stem, variant), so
    regenerating the bank yields identical ids (no autoincrement/random)."""
    slug = "".join(c for c in unit_id.lower() if c.isalnum() or c == "-")[:40]
    digest = hashlib.sha1(f"{unit_id}|{stem}|{variant}".encode()).hexdigest()[:8]
    return f"q-{slug}-{digest}"


# --- validation ----------------------------------------------------------------
def validate(q: Question) -> list[str]:
    """Return a list of human-readable problems ('' list = valid). Auditable, not
    a black box: every rule failure names itself."""
    errs: list[str] = []
    if not q.stem.strip():
        errs.append("empty stem")
    if not themes.is_valid(q.theme):
        errs.append(f"unknown theme {q.theme!r}")
    if q.kind not in KINDS:
        errs.append(f"unknown kind {q.kind!r}")
    if q.polarity not in POLARITIES:
        errs.append(f"unknown polarity {q.polarity!r}")
    if q.review_status not in REVIEW_STATUSES:
        errs.append(f"unknown review_status {q.review_status!r}")
    if q.distractor_strategy not in DISTRACTOR_STRATEGIES:
        errs.append(f"unknown distractor_strategy {q.distractor_strategy!r}")
    n = len(q.choices)
    if not (2 <= n <= 4):
        errs.append(f"{n} choices (expected 2–4, exam uses 3)")
    if any(not c.text.strip() and not c.image for c in q.choices):
        errs.append("a choice has neither text nor image")
    ncorrect = sum(1 for c in q.choices if c.is_correct)
    if not (1 <= ncorrect <= 2):
        errs.append(f"{ncorrect} correct choices (exam allows 1–2)")
    if ncorrect >= n:
        errs.append("every choice marked correct (no distractor)")
    if q.points <= 0:
        errs.append(f"non-positive points {q.points}")
    if q.kind == "figure_recognition" and not (q.image or any(c.image for c in q.choices)):
        errs.append("figure_recognition question has no image (stem or choices)")
    if not q.provenance.unit_id:
        errs.append("missing provenance.unit_id")
    return errs


# --- scoring (pure, swappable) -------------------------------------------------
def score(selected: list[int], correct: list[int], n_choices: int,
          points: int, mode: str) -> float:
    """Points earned for one question.

    all_or_nothing: full points iff the selected set matches the correct set
                    exactly (the Vaud "55/60 correct" reading).
    partial:        1/n of the points per option whose include/exclude judgment
                    is right (3 options × 1 pt = the 3-points-per-question split).
    """
    sel, cor = set(selected), set(correct)
    if mode == "all_or_nothing":
        return float(points) if sel == cor else 0.0
    if mode == "partial":
        right = sum(1 for i in range(n_choices) if (i in sel) == (i in cor))
        return round(points * right / n_choices, 3)
    raise ValueError(f"unknown scoring mode {mode!r}")


def grade_exam(questions: list[Question], answers: dict[str, list[int]],
               config: ExamConfig) -> dict:
    """Grade a full sitting. `answers` maps question id -> selected indices.
    Returns earned/total points and pass/fail under the config's threshold."""
    earned = 0.0
    for q in questions:
        earned += score(answers.get(q.id, []), q.correct, len(q.choices),
                         q.points, config.scoring)
    total = sum(q.points for q in questions)
    return {
        "earned": round(earned, 3),
        "total": total,
        "pass_points": config.pass_points,
        "fault_points": round(total - earned, 3),
        "passed": earned >= config.pass_points,
    }


# --- persistence (mirrors the KB store conventions) ----------------------------
DDL = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
CREATE TABLE IF NOT EXISTS questions (
    id                  TEXT PRIMARY KEY,
    theme               TEXT NOT NULL,
    kind                TEXT NOT NULL,
    polarity            TEXT NOT NULL,
    stem                TEXT NOT NULL,
    image               TEXT,
    points              INTEGER NOT NULL,
    explanation         TEXT,
    review_status       TEXT NOT NULL,
    distractor_strategy TEXT,
    generator           TEXT,
    prov_unit_id        TEXT NOT NULL,
    prov_ref            TEXT,
    prov_source         TEXT,
    prov_url            TEXT,
    prov_as_of          TEXT,
    prov_licence        TEXT
);
CREATE TABLE IF NOT EXISTS choices (
    question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    idx         INTEGER NOT NULL,
    text        TEXT,
    image       TEXT,
    is_correct  INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_q_theme   ON questions(theme);
CREATE INDEX IF NOT EXISTS idx_q_review  ON questions(review_status);
CREATE INDEX IF NOT EXISTS idx_ch_q      ON choices(question_id);
"""


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(DDL)
    return conn


def write_questions(conn: sqlite3.Connection, questions: list[Question]) -> None:
    """Idempotent upsert (replace by id), validating each first; raises on the
    first invalid question so a bad batch never half-lands."""
    for q in questions:
        problems = validate(q)
        if problems:
            raise ValueError(f"invalid question {q.id}: {'; '.join(problems)}")
    cur = conn.cursor()
    for q in questions:
        cur.execute("DELETE FROM questions WHERE id = ?", (q.id,))
        p = q.provenance
        cur.execute(
            """INSERT INTO questions
               (id, theme, kind, polarity, stem, image, points, explanation,
                review_status, distractor_strategy, generator,
                prov_unit_id, prov_ref, prov_source, prov_url, prov_as_of, prov_licence)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (q.id, q.theme, q.kind, q.polarity, q.stem, q.image, q.points,
             q.explanation, q.review_status, q.distractor_strategy, q.generator,
             p.unit_id, p.ref, p.source, p.url, p.as_of, p.licence))
        for i, c in enumerate(q.choices):
            cur.execute(
                "INSERT INTO choices (question_id, idx, text, image, is_correct) "
                "VALUES (?,?,?,?,?)", (q.id, i, c.text, c.image, int(c.is_correct)))
    conn.commit()


def set_meta(conn: sqlite3.Connection, **kv) -> None:
    cur = conn.cursor()
    for k, v in kv.items():
        cur.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?,?)", (k, str(v)))
    conn.commit()


def _row_to_question(conn: sqlite3.Connection, r: sqlite3.Row) -> Question:
    choices = [Choice(text=c["text"], image=c["image"], is_correct=bool(c["is_correct"]))
               for c in conn.execute(
                   "SELECT text, image, is_correct FROM choices "
                   "WHERE question_id=? ORDER BY idx", (r["id"],))]
    return Question(
        id=r["id"], theme=r["theme"], kind=r["kind"], polarity=r["polarity"],
        stem=r["stem"], image=r["image"], points=r["points"],
        explanation=r["explanation"], review_status=r["review_status"],
        distractor_strategy=r["distractor_strategy"], generator=r["generator"],
        choices=choices,
        provenance=Provenance(
            unit_id=r["prov_unit_id"], ref=r["prov_ref"], source=r["prov_source"],
            url=r["prov_url"], as_of=r["prov_as_of"], licence=r["prov_licence"]))


def load_questions(conn: sqlite3.Connection, review_status: str | None = None
                   ) -> list[Question]:
    """Read questions back, optionally filtered by review status (e.g. only
    EXPORTABLE_STATUSES for a public build)."""
    conn.row_factory = sqlite3.Row
    sql = "SELECT * FROM questions"
    args: tuple = ()
    if review_status:
        sql += " WHERE review_status = ?"
        args = (review_status,)
    rows = conn.execute(sql + " ORDER BY theme, id", args).fetchall()
    out = [_row_to_question(conn, r) for r in rows]
    conn.row_factory = None
    return out


def export_json(conn: sqlite3.Connection, path: str,
                exportable_only: bool = True) -> int:
    """Dump the bank to one JSON file (what the static player consumes). By
    default only review-cleared questions are emitted — the public licence/quality
    gate. Returns the number written."""
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM questions ORDER BY theme, id").fetchall()
    out = []
    for r in rows:
        if exportable_only and r["review_status"] not in EXPORTABLE_STATUSES:
            continue
        q = _row_to_question(conn, r)
        d = asdict(q)
        d["correct"] = q.correct          # convenience for the player
        out.append(d)
    meta = {k: v for k, v in conn.execute("SELECT key, value FROM meta")}
    conn.row_factory = None
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"meta": meta, "questions": out}, fh, ensure_ascii=False, indent=2)
    return len(out)
