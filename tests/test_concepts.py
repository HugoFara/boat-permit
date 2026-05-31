"""Tests for the "why" concept layer + principle tagger (roadmap group A/D1).

Covers: the additive Question.principle field, Concept persistence + the review
gate on export, and the deterministic principle classifier.
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.questions import schema                                    # noqa: E402
from src.questions.schema import Question, Choice, Provenance, Concept  # noqa: E402
from src.questions import principles                                # noqa: E402


def _conn():
    fd, path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    return schema.connect(path), path


def _q(qid="q1", theme="signalisation", stem="Stem?", choices=None, **kw):
    return Question(
        id=qid, theme=theme, kind="rule_mc", stem=stem,
        choices=choices or [Choice("a", is_correct=True), Choice("b")],
        provenance=Provenance(unit_id="u1", ref="r", source="s", url="http://x"),
        review_status="auto_approved", **kw)


def test_question_principle_roundtrips():
    conn, path = _conn()
    schema.write_questions(conn, [_q(principle="iala-buoyage")])
    got = schema.load_questions(conn)[0]
    assert got.principle == "iala-buoyage"
    # ships in the export (player join key)
    out = tempfile.mktemp(suffix=".json")
    schema.export_json(conn, out, exportable_only=True)
    assert json.load(open(out))["questions"][0]["principle"] == "iala-buoyage"
    os.remove(path); os.remove(out)


def test_concept_roundtrip_and_review_gate():
    conn, path = _conn()
    approved = Concept(id="c1", principle="iala-buoyage", kind="principle",
                       title="IALA", body="why", lang="fr",
                       prov_source="IALA R1001", review_status="approved")
    draft = Concept(id="c2", principle="nav-lights", kind="physical",
                    title="Lights", body="why", lang="fr")  # draft by default
    schema.write_concepts(conn, [approved, draft])
    assert len(schema.load_concepts(conn)) == 2
    # export honours the gate: only the approved concept ships
    out = tempfile.mktemp(suffix=".json")
    n = schema.export_concepts_json(conn, out, "fr", exportable_only=True)
    data = json.load(open(out))
    assert n == 1 and list(data.keys()) == ["iala-buoyage"]
    assert data["iala-buoyage"]["body"] == "why"
    os.remove(path); os.remove(out)


def test_concept_kind_validation():
    conn, path = _conn()
    bad = Concept(id="c", principle="p", kind="nonsense", title="t", body="b")
    try:
        schema.write_concepts(conn, [bad])
        assert False, "expected ValueError on unknown kind"
    except ValueError:
        pass
    os.remove(path)


def test_migration_is_additive_on_old_bank():
    """A bank created before the principle column / concepts table migrates
    cleanly without touching existing rows."""
    conn, path = _conn()
    schema.write_questions(conn, [_q()])
    # drop the new bits to simulate an older schema, then reconnect (migrates)
    conn.execute("DROP TABLE concepts")
    conn.commit(); conn.close()
    conn2 = schema.connect(path)
    cols = {r[1] for r in conn2.execute("PRAGMA table_info(questions)")}
    tbls = {r[0] for r in conn2.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert "principle" in cols and "concepts" in tbls
    assert schema.load_questions(conn2)[0].principle == ""  # backfilled blank
    os.remove(path)


def test_tagger_classifies_each_family():
    cases = {
        "Quelle est la signification de ce signal sonore : un son bref ?": "sound-signals",
        "Que signifie cette marque de jour en forme de ballon noir ?": "day-shapes",
        "Quel feu rouge un bateau à moteur montre-t-il à bâbord la nuit ?": "nav-lights",
        "Que signifie cette bouée latérale bâbord ?": "iala-buoyage",
        "Was bedeutet dieses Tafelzeichen am Ufer?": "waterway-signs",
        "Wer hat Vorfahrt beim Kreuzen zweier Boote?": "give-way",
        "Combien de gilets faut-il à bord ?": "",   # not in pilot scope
        # German declension / generic light-config phrasing the catalogue uses,
        # which the nominative/part-specific keys used to miss:
        "Wie lang ist die Dauer eines kurzen Tons?": "sound-signals",
        "Welches optische Zeichen ersetzt vier kurze Töne?": "sound-signals",
        "Welches Fahrzeug führt diese Lichter?": "nav-lights",
        "Was bedeuten zwei blaue Lichter übereinander?": "nav-lights",
    }
    for stem, expected in cases.items():
        assert principles.tag_for(stem) == expected, stem


def test_tagger_theme_fallback_and_accents():
    # unambiguous theme tags even without a keyword hit
    assert principles.tag_for("Identifiez ce signe.", theme="balisage") == "iala-buoyage"
    # accent-insensitive: "priorité" matches the de-accented keyword
    assert principles.tag_for("Qui a la priorité ?") == "give-way"


def test_tag_questions_fills_and_is_idempotent():
    conn, path = _conn()
    schema.write_questions(conn, [
        _q("a", stem="Que signifie ce feu rouge de bateau ?"),
        _q("b", theme="matelotage", stem="Comment faire un nœud de chaise ?"),
        _q("c", principle="hand-curated", stem="Quel feu montrer ?"),
    ])
    st = principles.tag_questions(conn)
    by_id = {q.id: q.principle for q in schema.load_questions(conn)}
    assert by_id["a"] == "nav-lights"     # tagged from text
    assert by_id["b"] == ""               # out of scope, left blank
    assert by_id["c"] == "hand-curated"   # existing tag preserved (no overwrite)
    assert st["tagged"] == 1
    # second run changes nothing
    st2 = principles.tag_questions(conn)
    assert st2["tagged"] == 0
    os.remove(path)


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")
