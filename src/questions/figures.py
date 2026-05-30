"""Templated figure-recognition question generator (Phase-2 step 3).

The deterministic, licence-clean seam: each signal/board figure becomes a
"Que signifie ce signal ?" question whose options are the figure's own caption
(correct) plus two **confusion-set** distractors — other figures from the same
annex and signal family (a prohibition board against other prohibition boards, a
coloured ball against other balls). That is where the difficulty lives: with only
two distractors, a random sibling would often be too easy or — worse — arguably
also correct, so distractors are filtered to be same-family yet non-overlapping.

Everything here is deterministic (stable ids, seeded ordering) so re-running
reproduces the bank exactly, and every question is `auto_approved` (no LLM, no
review needed) with full provenance back to its KB unit.
"""

from __future__ import annotations

import hashlib
import random
import re
import sqlite3

from .schema import Question, Choice, Provenance, make_question_id

# Licence gate: only public-domain federal law figures may go to the public bank.
_PUBLIC_DOMAIN_SOURCES = {"oni", "rnl"}

GENERATOR = "tmpl:figure_recognition.v1"

# Stem phrased to the signal family so it reads naturally. Signal-type detection
# is French-keyword-based, so the typed stems only fire for FR figures; DE/IT use
# the localized default (their captions classify as "autre"). Same diagram, asked
# in the figure's own language.
_STEM_BY_TYPE = {
    "interdiction": "Que signifie ce panneau ?",
    "autorisation": "Que signifie ce panneau ?",
    "obligation": "Que signifie ce panneau ?",
    "recommandation": "Que signifie ce panneau ?",
    "panneau": "Que signifie ce panneau ?",
    "feu": "Que signifie cette signalisation lumineuse ?",
    "cloche": "Que signifie ce signal sonore ?",
}
_STEM_DEFAULT_BY_LANG = {
    "fr": "Que signifie ce signal ?",
    "de": "Was bedeutet dieses Signal?",
    "it": "Che cosa significa questo segnale?",
}


def _stem(sigtype: str, lang: str) -> str:
    if lang == "fr":
        return _STEM_BY_TYPE.get(sigtype, _STEM_DEFAULT_BY_LANG["fr"])
    return _STEM_DEFAULT_BY_LANG.get(lang, _STEM_DEFAULT_BY_LANG["fr"])


def _seed(uid: str) -> int:
    """Process-stable seed (NOT builtin hash(), which is salted per run)."""
    return int(hashlib.sha1(uid.encode()).hexdigest()[:8], 16)


def _annex(ref: str) -> str:
    m = re.search(r"(Annexe [\w]+)", ref)
    return m.group(1) if m else "?"


def _signal_type(caption: str) -> str:
    c = caption.lower()
    for k in ("interdiction", "autorisation", "obligation", "recommandation"):
        if k in c:
            return k
    for k, tok in (("ballon", "ballon"), ("pavillon", "pavillon"), ("feu", "feu"),
                   ("bou", "bouee"), ("cloche", "cloche"), ("panneau", "panneau"),
                   ("cylindre", "cylindre"), ("cône", "cone"), ("flamme", "flamme")):
        if k in c:
            return tok
    return "autre"


def _normalize_caption(cap: str) -> str:
    cap = cap.strip().rstrip(":").strip()
    return cap[:1].upper() + cap[1:] if cap else cap


# Annex-title fallback prefixes, one per language (FR Annexe / DE Anhang / IT
# Allegato) — a caption that is just the annex heading, not a signal's meaning.
_ANNEX_PREFIXES = ("Annexe ", "Anhang ", "Allegato ")


def _recognizable(caption: str) -> bool:
    """A caption usable as a clean multiple-choice option / answer: atomic,
    short, not the article-embedded fallback ('ONI art. 5 – figure 1') nor the
    annex-title fallback ('Annexe 4 – Signaux …' / 'Anhang …' / 'Allegato …')."""
    if not caption or len(caption) > 55 or ";" in caption:
        return False
    if re.match(r"^(ONI|RNL)\b.*figure\s*\d", caption) or caption.startswith(_ANNEX_PREFIXES):
        return False
    return bool(re.search(r"[A-Za-zÀ-ÿ]{3,}", caption))


def _compatible(answer: str, cand: str) -> bool:
    """A candidate distractor is usable iff it is clearly a *different* meaning:
    not equal, neither a sub/superset of the answer (rules out "Interdiction de
    passer" vs "… pour bateaux motorisés"), and not a near-paraphrase."""
    a, c = answer.lower().strip(), cand.lower().strip()
    if a == c or a in c or c in a:
        return False
    ta, tc = set(re.findall(r"\w+", a)), set(re.findall(r"\w+", c))
    if not tc:
        return False
    return len(ta & tc) / len(ta | tc) < 0.7


def _choose_two(answer: str, pool: list[str], seed: int) -> list[str]:
    """Deterministically pick up to two mutually-distinct, answer-compatible
    captions from `pool`."""
    cands = sorted({p for p in pool if _compatible(answer, p)})
    random.Random(seed).shuffle(cands)
    picked: list[str] = []
    for c in cands:
        if len(picked) == 2:
            break
        if all(_compatible(c, p) for p in picked):
            picked.append(c)
    return picked


def _load_figures(kb: sqlite3.Connection) -> list[dict]:
    kb.row_factory = sqlite3.Row
    rows = kb.execute(
        """SELECT u.id, u.ref, u.theme, u.lang, u.source_id, u.source_name,
                  u.source_url, u.legal_version, u.licence, a.path, a.caption
           FROM units u JOIN assets a ON a.unit_id = u.id
           WHERE u.kind = 'annex_figure'""").fetchall()
    figs = []
    for r in rows:
        figs.append(dict(
            id=r["id"], ref=r["ref"], theme=r["theme"], lang=r["lang"],
            source_id=r["source_id"], source_name=r["source_name"],
            source_url=r["source_url"], legal_version=r["legal_version"],
            licence=r["licence"], image=r["path"], raw_caption=r["caption"],
            answer=_normalize_caption(r["caption"]), annex=_annex(r["ref"]),
            sigtype=_signal_type(r["caption"])))
    return figs


def build_figure_questions(kb: sqlite3.Connection) -> tuple[list[Question], dict]:
    """Generate figure-recognition questions from the KB. Returns (questions,
    stats). Stats record exactly what was dropped — no silent truncation."""
    figs = _load_figures(kb)
    stats = {"figures": len(figs), "non_public": 0, "not_recognizable": 0,
             "no_distractors": 0, "generated": 0,
             "by_strategy": {"confusion_set": 0, "sibling_random": 0},
             "by_theme": {}}

    # Distractor pool = recognizable, public-domain captions, indexed three ways
    # (tightest family first, widening on shortage).
    usable = [f for f in figs
              if f["source_id"] in _PUBLIC_DOMAIN_SOURCES and _recognizable(f["answer"])]
    # Pools are keyed by language too, so a question's distractors are always in
    # its own language (a German signal never gets a French distractor). FR keys
    # are unchanged in effect — every FR figure shares lang='fr' — so the FR bank
    # stays byte-identical.
    by_type: dict[tuple, list[str]] = {}
    by_annex: dict[tuple, list[str]] = {}
    by_theme: dict[tuple, list[str]] = {}
    for f in usable:
        by_type.setdefault((f["lang"], f["source_id"], f["annex"], f["sigtype"]), []).append(f["answer"])
        by_annex.setdefault((f["lang"], f["source_id"], f["annex"]), []).append(f["answer"])
        by_theme.setdefault((f["lang"], f["source_id"], f["theme"]), []).append(f["answer"])

    questions: list[Question] = []
    for f in figs:
        if f["source_id"] not in _PUBLIC_DOMAIN_SOURCES:
            stats["non_public"] += 1
            continue
        if not _recognizable(f["answer"]):
            stats["not_recognizable"] += 1
            continue

        ans = f["answer"]
        seed = _seed(f["id"])
        lang = f["lang"]
        tight = [c for c in by_type[(lang, f["source_id"], f["annex"], f["sigtype"])] if c != ans]
        picks = _choose_two(ans, tight, seed)
        strategy = "confusion_set"
        if len(picks) < 2:                      # widen: annex, then whole theme
            wider = ([c for c in by_annex[(lang, f["source_id"], f["annex"])] if c != ans]
                     + [c for c in by_theme[(lang, f["source_id"], f["theme"])] if c != ans])
            picks = _choose_two(ans, tight + wider, seed)
            strategy = "sibling_random"
        if len(picks) < 2:
            stats["no_distractors"] += 1
            continue

        stem = _stem(f["sigtype"], lang)
        options = [Choice(ans, is_correct=True)] + [Choice(p) for p in picks]
        random.Random(seed + 1).shuffle(options)   # answer not always first

        q = Question(
            id=make_question_id(f["id"], stem),
            theme=f["theme"], kind="figure_recognition", stem=stem, lang=lang,
            image=f["image"], choices=options,
            provenance=Provenance(
                unit_id=f["id"], ref=f["ref"], source=f["source_name"],
                url=f["source_url"], as_of=f["legal_version"], licence=f["licence"]),
            explanation=f"{f['ref']} — « {ans} ».",
            review_status="auto_approved", distractor_strategy=strategy,
            generator=GENERATOR)
        questions.append(q)
        stats["generated"] += 1
        stats["by_strategy"][strategy] += 1
        stats["by_theme"][f["theme"]] = stats["by_theme"].get(f["theme"], 0) + 1

    kb.row_factory = None
    return questions, stats
