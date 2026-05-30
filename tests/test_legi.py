"""Tests for the France law ingestion (`src/fr/legi.py`).

France grounds its bank in the actual statute: `legi.py` ingests the Code des
transports (4ᵉ partie — navigation intérieure, the RGP) from the official DILA
LEGI open data into `src/fr/legi_kb.json`. These checks run off that *committed*
corpus (no 1.2 GB dump needed), pin its shape, and — crucially — assert that every
Code-des-transports article our seed bank cites actually exists in the ingested
law, so a citation can never silently drift from the source again.

Run with `python tests/test_legi.py`.
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import themes                       # noqa: E402
from src.fr import themes_fr                 # noqa: E402  (registers FR themes)
from src.fr.seed_fr import SEED              # noqa: E402

CORPUS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "src", "fr", "legi_kb.json")
_CITE = re.compile(r"art\.?\s*([LRAD]\.?\s?4\d{3}[\d-]*)", re.I)


def _key(num: str) -> str:
    return num.upper().replace(".", "").replace(" ", "")


def _corpus():
    with open(CORPUS, encoding="utf-8") as fh:
        return json.load(fh)


def test_corpus_is_well_formed():
    doc = _corpus()
    assert doc["meta"].get("country") == "FR" and doc["meta"].get("source") == "legi"
    units = doc["units"]
    assert len(units) > 1000, "expected the full Part-4 inland-navigation corpus"
    for u in units:
        assert u["source_id"] == "code_transports"
        assert u["ref"].startswith("Code des transports, art. ")
        assert u["text"].strip(), f"{u['ref']}: empty text"
        assert u["source_url"].startswith("https://www.legifrance.gouv.fr/")
        assert "Etalab" in u["licence"]
        assert themes.is_valid(u["theme"]), f"{u['ref']}: bad theme {u['theme']!r}"


def test_every_cited_code_des_transports_article_exists_in_the_law():
    nums = {_key(u["ref"].split("art. ", 1)[1]) for u in _corpus()["units"]}
    missing: dict[str, list[int]] = {}
    cited = 0
    for i, e in enumerate(SEED):
        for m in _CITE.finditer(e["ref"]):
            cited += 1
            k = _key(m.group(1))
            if k not in nums:
                missing.setdefault(k, []).append(i)
    assert cited >= 15, "expected the RGP citations to be present in the seed"
    assert not missing, (
        "seed cites Code-des-transports articles absent from the ingested law: "
        + ", ".join(f"{k} (seed #{v})" for k, v in sorted(missing.items())))


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
    print(f"\n{len(tests)} tests passed")
