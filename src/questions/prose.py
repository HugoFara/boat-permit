"""LLM-drafted question generator for the prose/law themes (Phase-2 step 5).

Figures are templated and deterministic (`figures.py`); everything else — Lois,
Météo, Matelotage, Définitions, Eaux frontalières — is *drafted* from the KB's
primary-source text by a language model, then **held for human review**. Nothing
here is trusted on sight:

  * questions are built only from a KB unit's own text (licence-clean, provenance
    attached), and the prompt forbids outside facts;
  * every draft lands as `review_status="pending"` — the export gate keeps it out
    of the public bank until a human approves it (`run.py review`);
  * a grounding check flags drafts whose correct answer isn't supported by the
    source text, surfacing likely hallucinations to the reviewer.

The drafter is swappable (`Drafter` protocol): `AnthropicDrafter` for real
generation, any callable for tests/offline. The pipeline — selection, prompting,
parsing, grounding, validation, gating — is identical regardless.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from typing import Callable, Protocol

from .schema import Question, Choice, Provenance, make_question_id, validate

# KB theme -> question kind (all in schema.KINDS). Theme ids are unique across the
# per-country taxonomies (src/themes.py, countries/de_themes.py, countries/
# intl_themes.py), so one merged map serves every language; anything not listed
# (German verkehrsregeln/…, all COLREG themes) falls through to "rule_mc".
_KIND_BY_THEME = {
    # Switzerland (fr)
    "definitions": "definition_mc",
    "meteorologie": "meteo_mc",
    "matelotage": "matelotage_mc",
    "eaux_frontalieres": "frontiere_mc",
    "lois": "rule_mc",
    "signalisation": "rule_mc",
    # Germany (de) — the distinctively-typed themes; the rest default to rule_mc
    "definitionen": "definition_mc",
    "wetterkunde": "meteo_mc",
}

# Themes drafted here (signalisation is covered by templated figures instead).
PROSE_THEMES = ("definitions", "meteorologie", "matelotage", "eaux_frontalieres", "lois")

_MIN_LEN, _MAX_LEN = 200, 2200      # tractable, self-contained source chunks
DEFAULT_MODEL = "claude-sonnet-4-6"


# --- source selection ----------------------------------------------------------
def select_units(kb: sqlite3.Connection, theme: str, limit: int = 0,
                 lang: str = "fr") -> list[dict]:
    """Prose/article KB units of a theme + language that are substantial enough to
    ask about and short enough to draft from cleanly. Figures are excluded
    (templated). The lang filter matters since the KB is multilingual — drafting
    must target one language at a time."""
    kb.row_factory = sqlite3.Row
    rows = kb.execute(
        """SELECT id, ref, title, text, theme, lang, source_name, source_url,
                  legal_version, licence
           FROM units
           WHERE theme = ? AND lang = ? AND kind != 'annex_figure'
                 AND length(text) BETWEEN ? AND ?
           ORDER BY length(text) DESC""",
        (theme, lang, _MIN_LEN, _MAX_LEN)).fetchall()
    out = [dict(r) for r in rows]
    return out[:limit] if limit else out


# --- prompting -----------------------------------------------------------------
_SCHEMA_HINT = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "stem": {"type": "string", "description": "The question stem, in the exam language."},
                    "polarity": {"type": "string", "enum": ["affirmative", "negative"]},
                    "choices": {
                        "type": "array", "minItems": 3, "maxItems": 3,
                        "items": {
                            "type": "object",
                            "properties": {
                                "text": {"type": "string"},
                                "correct": {"type": "boolean"},
                            },
                            "required": ["text", "correct"],
                        },
                    },
                    "explanation": {"type": "string",
                                    "description": "A brief justification citing the source article/rule."},
                },
                "required": ["stem", "polarity", "choices", "explanation"],
            },
        }
    },
    "required": ["questions"],
}


def _prompt_fr(unit: dict, n_questions: int) -> str:
    return f"""Tu rédiges des questions d'examen pour le permis de conduire un bateau \
(catégorie A, Suisse, lac Léman), à partir UNIQUEMENT du texte juridique fourni \
ci-dessous. N'utilise aucune connaissance extérieure ; chaque réponse correcte \
doit être justifiable par le texte seul.

Règles :
- Rédige {n_questions} question(s) en français.
- Exactement 3 propositions par question, dont 1 ou 2 correctes (comme à l'examen).
- Les distracteurs doivent être plausibles mais clairement FAUX d'après le texte \
(pas de piège ambigu, pas de distracteur qui pourrait aussi être correct).
- « polarity » = « negative » si l'énoncé demande ce qui n'est PAS le cas \
(« Laquelle de ces affirmations est fausse ? »), sinon « affirmative ».
- « explanation » : une phrase citant la référence ({unit['ref']}).
- Ne reproduis pas mot pour mot une banque de questions existante ; formule \
toi-même à partir du texte.

Référence : {unit['ref']} — {unit['title']}

Texte source :
\"\"\"
{unit['text']}
\"\"\"
"""


def _prompt_de(unit: dict, n_questions: int) -> str:
    return f"""Du formulierst Prüfungsfragen für die Bootsführerschein-Theorieprüfung \
AUSSCHLIESSLICH auf Grundlage des unten stehenden Rechtstextes. Verwende KEIN \
Wissen von außerhalb; jede richtige Antwort muss allein aus dem Text belegbar sein.

Regeln:
- Formuliere {n_questions} Frage(n) auf Deutsch.
- Genau 3 Antwortmöglichkeiten je Frage, davon 1 oder 2 richtig (wie in der Prüfung).
- Die Distraktoren müssen plausibel, aber laut Text eindeutig FALSCH sein \
(keine mehrdeutige Falle, kein Distraktor, der auch richtig sein könnte).
- „polarity“ = „negative“, wenn die Frage danach fragt, was NICHT zutrifft \
(„Welche Aussage ist falsch?“), sonst „affirmative“.
- „explanation“: ein Satz mit Bezug auf die Fundstelle ({unit['ref']}).
- Gib keine bestehende Fragensammlung wörtlich wieder; formuliere selbst aus dem Text.

Fundstelle: {unit['ref']} — {unit['title']}

Quelltext:
\"\"\"
{unit['text']}
\"\"\"
"""


def _prompt_en(unit: dict, n_questions: int) -> str:
    return f"""You are writing exam questions for a boating theory exam, based ONLY \
on the legal/regulatory text provided below. Use NO outside knowledge; every \
correct answer must be justifiable from the text alone.

Rules:
- Write {n_questions} question(s) in English.
- Exactly 3 options per question, of which 1 or 2 are correct (as in the exam).
- Distractors must be plausible but clearly FALSE according to the text \
(no ambiguous traps, no distractor that could also be correct).
- "polarity" = "negative" if the stem asks what is NOT the case \
("Which of these statements is false?"), otherwise "affirmative".
- "explanation": one sentence citing the reference ({unit['ref']}).
- Do not reproduce any existing question bank verbatim; formulate your own from the text.

Reference: {unit['ref']} — {unit['title']}

Source text:
\"\"\"
{unit['text']}
\"\"\"
"""


_PROMPTS: dict[str, Callable[[dict, int], str]] = {
    "fr": _prompt_fr, "de": _prompt_de, "en": _prompt_en,
}


def build_prompt(unit: dict, n_questions: int, lang: str = "fr") -> str:
    """A strict, source-grounded drafting instruction in ``lang``. The model may
    use ONLY the supplied text — this is what keeps questions licence-clean and
    factual. Unknown languages fall back to French (the project's base language)."""
    return _PROMPTS.get(lang, _prompt_fr)(unit, n_questions)


# --- drafter (swappable) -------------------------------------------------------
class Drafter(Protocol):
    name: str
    def draft(self, prompt: str) -> str:    # returns raw JSON (the _SCHEMA_HINT shape)
        ...


class CallableDrafter:
    """Wrap any prompt->json-string function (tests, offline, stubs)."""
    def __init__(self, fn: Callable[[str], str], name: str = "callable"):
        self._fn, self.name = fn, name

    def draft(self, prompt: str) -> str:
        return self._fn(prompt)


class AnthropicDrafter:
    """Real generation via the Anthropic API, forcing the JSON schema through a
    tool call. Needs `anthropic` installed and ANTHROPIC_API_KEY set."""
    def __init__(self, model: str = DEFAULT_MODEL, max_tokens: int = 2000):
        import anthropic                      # lazy: module usable without the SDK
        self._client = anthropic.Anthropic()
        self.model = model
        self.max_tokens = max_tokens
        self.name = f"llm:{model}"

    def draft(self, prompt: str) -> str:
        msg = self._client.messages.create(
            model=self.model, max_tokens=self.max_tokens,
            tools=[{"name": "emit_questions",
                    "description": "Emit the drafted exam questions.",
                    "input_schema": _SCHEMA_HINT}],
            tool_choice={"type": "tool", "name": "emit_questions"},
            messages=[{"role": "user", "content": prompt}])
        for block in msg.content:
            if getattr(block, "type", None) == "tool_use":
                return json.dumps(block.input, ensure_ascii=False)
        raise RuntimeError("model returned no tool_use block")


# --- parsing + grounding -------------------------------------------------------
# Grounding is lexical, so the alphabet + stopword set are language-specific. The
# regex only keeps tokens of length ≥4, so short function words (der/die/the/les)
# never appear and need not be listed. FR is preserved exactly (byte-stable bank).
_LETTERS = {
    "fr": "a-zàâäéèêëîïôöùûüç",
    "de": "a-zäöüß",
    "en": "a-z",
}
_STOP_BY_LANG: dict[str, set[str]] = {
    "fr": {"dans", "pour", "avec", "sans", "leur", "elle", "être", "cette", "plus",
           "doit", "doivent", "peut", "peuvent", "tous", "toute", "toutes", "selon",
           "lorsque", "ainsi", "entre", "aussi", "lequel", "laquelle", "quelle"},
    "de": {"oder", "eine", "einen", "einem", "eines", "einer", "sind", "wird",
           "werden", "muss", "müssen", "kann", "können", "darf", "dürfen", "nicht",
           "auch", "wenn", "sowie", "über", "unter", "durch", "diese", "dieser",
           "dieses", "sich", "dass", "nach", "beim", "sein", "seine", "ihre",
           "alle", "allen", "aller", "sowohl", "wie"},
    "en": {"that", "this", "these", "those", "which", "shall", "must", "with",
           "from", "into", "when", "than", "such", "each", "other", "also", "upon",
           "within", "their", "there", "where", "while", "they", "them", "have",
           "been", "being", "does", "then", "whether", "under", "over", "between",
           "because", "about", "would", "could", "should", "whose", "they"},
}


def _content_words(s: str, lang: str = "fr") -> set[str]:
    cls = _LETTERS.get(lang, _LETTERS["fr"])
    stop = _STOP_BY_LANG.get(lang, _STOP_BY_LANG["fr"])
    return {w for w in re.findall(rf"[{cls}]{{4,}}", s.lower()) if w not in stop}


def grounding_score(answer_text: str, source_text: str, lang: str = "fr") -> float:
    """Fraction of the correct answer's content words that appear in the source.
    Low = the answer may be invented (or merely paraphrased) → reviewer should
    look closely. 1.0 = every content word is anchored in the text. ``lang`` picks
    the alphabet + stopwords (defaults to French)."""
    aw = _content_words(answer_text, lang)
    if not aw:
        return 1.0
    sw = _content_words(source_text, lang)
    return round(len(aw & sw) / len(aw), 3)


def parse_drafts(raw: str, unit: dict) -> list[Question]:
    """Turn the drafter's JSON into Question objects (review_status=pending)."""
    data = json.loads(raw)
    items = data["questions"] if isinstance(data, dict) else data
    kind = _KIND_BY_THEME.get(unit["theme"], "rule_mc")
    out: list[Question] = []
    for i, it in enumerate(items):
        choices = [Choice(text=c["text"].strip(), is_correct=bool(c.get("correct")))
                   for c in it["choices"]]
        out.append(Question(
            id=make_question_id(unit["id"], it["stem"], f"v{i}"),
            theme=unit["theme"], kind=kind, stem=it["stem"].strip(),
            lang=unit.get("lang", "fr"),
            choices=choices, polarity=it.get("polarity", "affirmative"),
            points=3, explanation=it.get("explanation", "").strip(),
            review_status="pending", distractor_strategy="n/a",
            generator=unit.get("_generator", "llm"),
            provenance=Provenance(
                unit_id=unit["id"], ref=unit["ref"], source=unit["source_name"],
                url=unit["source_url"], as_of=unit["legal_version"],
                licence=unit["licence"])))
    return out


def seed_questions(kb: sqlite3.Connection, entries: list[dict],
                   generator: str = "seed:curated.v1",
                   is_valid_theme: Callable[[str], bool] | None = None
                   ) -> tuple[list[Question], dict]:
    """Load hand-authored seed drafts (keyed by KB unit ref) through the same
    grounding + validation path as the LLM drafter, as `pending`. Returns
    (questions, stats). An entry whose ref isn't in the KB, or whose answer isn't
    grounded, is skipped and counted."""
    kb.row_factory = sqlite3.Row
    stats = {"entries": len(entries), "kept": 0, "missing_unit": 0,
             "invalid": 0, "weak_grounding": 0}
    out: list[Question] = []
    for i, e in enumerate(entries):
        u = kb.execute(
            "SELECT id, ref, theme, lang, source_name, source_url, legal_version, "
            "licence, text FROM units WHERE ref = ? AND lang = ? LIMIT 1",
            (e["ref"], e.get("lang", "fr"))).fetchone()
        if u is None:
            stats["missing_unit"] += 1
            continue
        kind = _KIND_BY_THEME.get(u["theme"], "rule_mc")
        q = Question(
            id=make_question_id(u["id"], e["stem"], f"seed{i}"),
            theme=u["theme"], kind=kind, stem=e["stem"], lang=u["lang"],
            choices=[Choice(text=t, is_correct=c) for t, c in e["choices"]],
            polarity=e.get("polarity", "affirmative"), points=3,
            explanation=e.get("explanation", ""), review_status="pending",
            distractor_strategy="curated", generator=generator,
            provenance=Provenance(
                unit_id=u["id"], ref=u["ref"], source=u["source_name"],
                url=u["source_url"], as_of=u["legal_version"], licence=u["licence"]))
        errs = validate(q) if is_valid_theme is None else validate(q, is_valid_theme)
        if errs:
            stats["invalid"] += 1
            continue
        correct = " ".join(c.text for c in q.choices if c.is_correct)
        if grounding_score(correct, u["text"], u["lang"]) < 0.34:
            stats["weak_grounding"] += 1
            continue
        out.append(q)
        stats["kept"] += 1
    return out, stats


def draft_for_theme(kb: sqlite3.Connection, drafter: Drafter, theme: str,
                    limit: int = 0, per_unit: int = 2,
                    min_grounding: float = 0.34, lang: str = "fr",
                    is_valid_theme: Callable[[str], bool] | None = None
                    ) -> tuple[list[Question], dict]:
    """Draft questions for one theme + language. Returns (pending questions,
    stats). Drops schema-invalid drafts and those whose correct answer is too
    weakly grounded in the source (likely hallucination); the rest are kept for
    human review. ``is_valid_theme`` lets a non-Swiss country validate against its
    own taxonomy (e.g. ``intl.COUNTRY.themes.__contains__``); ``None`` keeps the
    default Swiss validator so the CH path is unchanged."""
    units = select_units(kb, theme, limit, lang)
    stats = {"theme": theme, "units": len(units), "drafted": 0, "kept": 0,
             "invalid": 0, "weak_grounding": 0, "errored": 0}
    kept: list[Question] = []
    for u in units:
        u["_generator"] = drafter.name
        try:
            raw = drafter.draft(build_prompt(u, per_unit, lang))
            drafts = parse_drafts(raw, u)
        except Exception:
            stats["errored"] += 1
            continue
        for q in drafts:
            stats["drafted"] += 1
            errs = validate(q) if is_valid_theme is None else validate(q, is_valid_theme)
            if errs:
                stats["invalid"] += 1
                continue
            correct_text = " ".join(c.text for c in q.choices if c.is_correct)
            if grounding_score(correct_text, u["text"], lang) < min_grounding:
                stats["weak_grounding"] += 1
                continue
            kept.append(q)
            stats["kept"] += 1
    return kept, stats
