"""Tests for question derivation from the ingested law (`src/fr/derive_fr.py`).

Derived questions are drafted *from* a real Code-des-transports / Division-245 /
décret article (grounded in the source, not recall) and held as `pending` in the
committed `src/fr/derived_drafts.json` until reviewed. These checks pin that each
draft is well-formed, is linked to an article that actually exists in the ingested
corpus, and — the review gate — that only `approved` drafts are ever served.

Run with `python tests/test_derive.py`.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.fr import themes_fr, derive_fr, build_fr   # noqa: E402
from src.fr.seed_fr import SEED                      # noqa: E402

CORPUS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "src", "fr", "legi_kb.json")


def _kb_articles():
    return {(u["source_id"], u["ref"].split("art. ", 1)[1])
            for u in json.load(open(CORPUS, encoding="utf-8"))["units"]}


def _ref_units():
    import json
    return {u["ref"] for u in json.load(open(derive_fr.REF_JSON, encoding="utf-8"))["units"]}


def test_drafts_are_well_formed_and_grounded():
    drafts = derive_fr.load_drafts()
    assert drafts, "expected derived drafts"
    kb = _kb_articles()          # LEGI law (eaux) by (source, num)
    refs = _ref_units()          # IALA/SHOM reference (côtière) by ref
    for d in drafts:
        assert d["status"] in {"pending", "approved", "rejected"}
        assert d["generator"].startswith("derive:")
        assert derive_fr._validate(d) == [], f"{d['ref']}: {derive_fr._validate(d)}"
        # every draft is tied to a real unit in an ingested corpus
        a = d["article"]
        if "num" in a:           # LEGI article
            assert (a["source_id"], a["num"]) in kb, f"{d['ref']}: article not in KB"
            assert d["ref"].endswith(a["num"])
        else:                    # reference fact (côtière)
            assert a["unit_ref"] in refs, f"{d['ref']}: reference unit not in KB"
            assert d["ref"] == a["unit_ref"]


def test_only_approved_drafts_are_served():
    drafts = derive_fr.load_drafts()
    approved = [d for d in drafts if d["status"] == "approved"]
    by_opt = build_fr.build_questions()
    total_fr = sum(len(by_lang["fr"]) for by_lang in by_opt.values())
    # served bank = the hand-authored seed + only the approved derived drafts;
    # every pending/rejected draft is excluded.
    assert total_fr == len(SEED) + len(approved)
    # approved drafts must sit in their option's theme set
    for d in approved:
        assert d["theme"] in themes_fr.OPTION_THEMES[d["option"]]


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
    print(f"\n{len(tests)} tests passed")
