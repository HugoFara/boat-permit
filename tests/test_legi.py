"""Tests for the France law ingestion (`src/fr/legi.py`).

France grounds its bank in the actual statute: `legi.py` ingests the texts the
seed cites — Code des transports (4ᵉ partie, the RGP), Code de l'environnement
(L.218-x rejets), the Décret 2007-1167 + Arrêté du 28 sept 2007 (permis), and the
Arrêté du 10 fév 2016 (Division 245) — from the official DILA LEGI open data into
the committed corpus `src/fr/legi_kb.json`.

These checks run off that corpus (no 1.2 GB dump needed), pin its shape, and —
crucially — assert that every article our seed cites in an *ingested* text exists
in the law, reusing `legi`'s own citation matcher so the test and the tool agree.
A citation can never silently drift from the source again.

Run with `python tests/test_legi.py`.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import themes                       # noqa: E402
from src.fr import themes_fr, legi           # noqa: E402  (themes_fr registers FR themes)
from src.fr.seed_fr import SEED              # noqa: E402

CORPUS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "src", "fr", "legi_kb.json")
INGESTED_SOURCES = {t.source_id for t in legi.TEXTS}


def _corpus():
    with open(CORPUS, encoding="utf-8") as fh:
        return json.load(fh)


def test_corpus_is_well_formed():
    doc = _corpus()
    assert doc["meta"].get("country") == "FR" and doc["meta"].get("source") == "legi"
    units = doc["units"]
    assert len(units) > 1300, "expected all five ingested texts"
    present = {u["source_id"] for u in units}
    assert INGESTED_SOURCES <= present, f"missing sources: {INGESTED_SOURCES - present}"
    for u in units:
        assert u["source_id"] in INGESTED_SOURCES
        assert u["text"].strip(), f"{u['ref']}: empty text"
        assert u["source_url"].startswith("https://www.legifrance.gouv.fr/")
        assert "Etalab" in u["licence"]
        assert themes.is_valid(u["theme"]), f"{u['ref']}: bad theme {u['theme']!r}"


def test_every_cited_article_of_an_ingested_text_exists_in_the_law():
    # Build {kb_source: {article keys}} from the committed corpus.
    nums: dict[str, set] = {}
    for u in _corpus()["units"]:
        nums.setdefault(u["source_id"], set()).add(
            legi._artkey(u["ref"].split("art. ", 1)[1]))
    missing: dict[str, list[int]] = {}
    matched = 0
    for i, e in enumerate(SEED):
        kb = legi._SEED_SRC_TO_KB.get(e["source"])
        if not kb:                       # source not ingested (COLREG/IALA/ITU/…)
            continue
        for m in legi._ART.finditer(e["ref"]):
            tok = legi._artkey(m.group(1))
            if tok in nums.get(kb, set()):
                matched += 1
            else:
                missing.setdefault(f"{kb}:{tok}", []).append(i)
    assert matched >= 30, "expected the RGP/permit/env citations to be checked"
    assert not missing, (
        "seed cites articles absent from the ingested law: "
        + ", ".join(f"{k} (seed #{v})" for k, v in sorted(missing.items())))


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
    print(f"\n{len(tests)} tests passed")
