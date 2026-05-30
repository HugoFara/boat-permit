"""Tests for the LLM-draft prose pipeline (`src/questions/prose.py`): grounding
guard, draft parsing, the drop-weak-grounding behaviour, and the seed loader —
all offline with a tiny in-memory KB and a canned drafter.

Run with `python tests/test_prose.py`.
"""

import os
import sys
import json
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.questions import prose, validate  # noqa: E402


def _kb():
    """Minimal in-memory KB with the columns the pipeline reads."""
    c = sqlite3.connect(":memory:")
    c.execute("""CREATE TABLE units (id TEXT, ref TEXT, title TEXT, text TEXT,
                 theme TEXT, kind TEXT, source_name TEXT, source_url TEXT,
                 legal_version TEXT, licence TEXT, lang TEXT)""")
    c.execute("INSERT INTO units VALUES (?,?,?,?,?,?,?,?,?,?,?)",
              ("u-frontiere", "RNL art. 64", "Priorités",
               "Tout bateau doit s'écarter d'un bateau incapable de manœuvrer "
               "qui signale sa présence. En cas de rencontre et de dépassement, "
               "tout bateau doit s'écarter des bateaux à passagers prioritaires "
               "et des convois remorqués, puis des bateaux à marchandises, puis "
               "des bateaux de pêche professionnelle en opération.",
               "eaux_frontalieres", "article", "RNL", "https://x",
               "2019-06-01", "Public domain", "fr"))
    c.commit()
    return c


def test_grounding_score():
    src = "le bateau motorisé est un bateau à propulsion mécanique"
    assert prose.grounding_score("propulsion mécanique", src) == 1.0
    assert prose.grounding_score("licorne arc-en-ciel téléportation", src) == 0.0


def test_select_and_prompt():
    kb = _kb()
    units = prose.select_units(kb, "eaux_frontalieres")
    assert len(units) == 1 and units[0]["ref"] == "RNL art. 64"
    p = prose.build_prompt(units[0], 2)
    assert "RNL art. 64" in p and "UNIQUEMENT" in p   # source-grounded instruction


def test_build_prompt_is_language_specific():
    u = {"ref": "COLREG Rule 5", "title": "Look-out", "text": "Every vessel …",
         "theme": "steering_sailing", "lang": "en"}
    en = prose.build_prompt(u, 2, "en")
    de = prose.build_prompt(u, 2, "de")
    fr = prose.build_prompt(u, 2, "fr")
    assert "Write 2 question(s) in English." in en and "COLREG Rule 5" in en
    assert "Frage(n) auf Deutsch" in de and "COLREG Rule 5" in de
    assert "en français" in fr                       # the FR template, unchanged
    # an unknown language falls back to the French base template
    assert prose.build_prompt(u, 2, "xx") == fr
    assert prose.build_prompt(u, 2) == fr             # default stays French


def test_grounding_is_language_aware():
    # German: umlaut/ß words are content words and match the source
    de_src = "Die Ausweichregeln gelten für alle Fahrzeuge auf dem Bodensee."
    assert prose.grounding_score("Ausweichregeln Fahrzeuge", de_src, "de") == 1.0
    assert prose.grounding_score("Einhorn Teleportation", de_src, "de") == 0.0
    # English
    en_src = "Every vessel shall maintain a proper look-out by sight and hearing."
    assert prose.grounding_score("proper look-out", en_src, "en") == 1.0
    # French behaviour is unchanged (default lang)
    assert prose.grounding_score("propulsion mécanique",
                                 "à propulsion mécanique", "fr") == 1.0


def test_parse_sets_pending_and_kind():
    unit = {"id": "u1", "ref": "RNL art. 64", "title": "t", "text": "x",
            "theme": "eaux_frontalieres", "source_name": "RNL", "source_url": "u",
            "legal_version": "2019-06-01", "licence": "PD", "_generator": "llm:test"}
    raw = json.dumps({"questions": [{
        "stem": "Q ?", "polarity": "affirmative",
        "choices": [{"text": "a", "correct": True}, {"text": "b", "correct": False},
                    {"text": "c", "correct": False}],
        "explanation": "RNL art. 64"}]})
    qs = prose.parse_drafts(raw, unit)
    assert len(qs) == 1
    q = qs[0]
    assert q.review_status == "pending"
    assert q.kind == "frontiere_mc"           # mapped from theme
    assert q.generator == "llm:test"
    assert q.provenance.as_of == "2019-06-01"


def test_draft_drops_ungrounded():
    kb = _kb()
    # drafter that returns a well-formed but invented answer
    def fake(_prompt):
        return json.dumps({"questions": [{
            "stem": "Q ?", "polarity": "affirmative",
            "choices": [{"text": "licorne téléportation quantique", "correct": True},
                        {"text": "distracteur faux un", "correct": False},
                        {"text": "distracteur faux deux", "correct": False}],
            "explanation": "x"}]})
    qs, st = prose.draft_for_theme(kb, prose.CallableDrafter(fake), "eaux_frontalieres")
    assert st["drafted"] == 1 and st["kept"] == 0 and st["weak_grounding"] == 1
    assert qs == []


def test_draft_keeps_grounded():
    kb = _kb()
    def fake(_prompt):
        return json.dumps({"questions": [{
            "stem": "Que doit faire tout bateau ?", "polarity": "affirmative",
            "choices": [{"text": "s'écarter du bateau incapable de manœuvrer", "correct": True},
                        {"text": "maintenir son cap", "correct": False},
                        {"text": "accélérer", "correct": False}],
            "explanation": "RNL art. 64"}]})
    qs, st = prose.draft_for_theme(kb, prose.CallableDrafter(fake), "eaux_frontalieres")
    assert st["kept"] == 1 and validate(qs[0]) == []
    assert qs[0].review_status == "pending"


def test_seed_loader():
    kb = _kb()
    seed = [{"ref": "RNL art. 64", "polarity": "affirmative",
             "stem": "Que doit faire tout bateau face à un bateau incapable de manœuvrer ?",
             "choices": [("s'écarter de ce bateau", True),
                         ("maintenir son cap", False),
                         ("le dépasser", False)],
             "explanation": "RNL art. 64"},
            {"ref": "INEXISTANT", "polarity": "affirmative", "stem": "?",
             "choices": [("a", True), ("b", False), ("c", False)], "explanation": ""}]
    qs, st = prose.seed_questions(kb, seed)
    assert st["kept"] == 1 and st["missing_unit"] == 1
    assert qs[0].review_status == "pending" and qs[0].generator == "seed:curated.v1"
    assert qs[0].distractor_strategy == "curated"


def test_select_units_uncapped_is_a_superset():
    # The ingest path (tools/subagent_draft.cmd_ingest) matches committed answers
    # against UNCAPPED select_units(limit=0); a positive limit only bounds the *emit*
    # drafting budget. This guards the fix that recovered the stranded CH/fr
    # matelotage+météo questions — a later-tightened plan cap must never silently
    # drop a committed answer at ingest time.
    c = sqlite3.connect(":memory:")
    c.execute("""CREATE TABLE units (id TEXT, ref TEXT, title TEXT, text TEXT,
                 theme TEXT, kind TEXT, source_name TEXT, source_url TEXT,
                 legal_version TEXT, licence TEXT, lang TEXT)""")
    base = "Le matelotage couvre les nœuds, l'amarrage et le mouillage du bateau. "
    for i in range(5):
        c.execute("INSERT INTO units VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                  (f"u{i}", f"Matelotage — unité {i}", "Nœud", base * (8 - i),
                   "matelotage", "article", "WP", "https://x", "", "CC", "fr"))
    c.commit()
    full = prose.select_units(c, "matelotage", limit=0, lang="fr")
    capped = prose.select_units(c, "matelotage", limit=2, lang="fr")
    assert len(full) == 5 and len(capped) == 2
    assert {u["ref"] for u in capped} < {u["ref"] for u in full}   # cap strands units


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
    print(f"\n{len(tests)} tests passed")
