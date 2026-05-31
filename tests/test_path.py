"""Tests for the path-to-permit scaffolding (`Country.path` / `PathStep`).

The non-theory steps (age / medical / practical / application / fees / validity)
are procedural reference data authored from official sources. These checks pin the
discipline: every step is well-formed and sourced (source + url + ISO ``as_of``),
its ``region_scope`` / ``permit_scope`` resolve to real regions/permits, the
default-language body is present, the path manifest is ordered + JSON-serialisable,
the staleness snapshot fingerprints each country's path, and the generated country
doc sections stay in sync with the data (single source of truth).

Run with `python tests/test_path.py`.
"""

import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import countries, staleness          # noqa: E402
from src.countries.base import Country         # noqa: E402

KNOWN_CODES = set(Country._PATH_ORDER)
WITH_PATH = [countries.get(code) for code in countries.codes()
             if countries.get(code).path]


def test_expected_countries_have_path():
    codes = {c.code for c in WITH_PATH}
    assert {"CH", "DE", "FR"} <= codes
    assert "INT" not in codes        # sourcing-only member: no permits ⇒ no path


def test_steps_well_formed_and_sourced():
    for c in WITH_PATH:
        for s in c.path:
            assert s.code in KNOWN_CODES, (c.code, s.code)
            assert s.source, (c.code, s.code)
            assert s.url.startswith("http"), (c.code, s.code, s.url)
            dt.date.fromisoformat(s.as_of)               # ISO date or raises
            assert isinstance(s.body, dict) and s.body, (c.code, s.code)
            body = s.body.get(c.default_lang)
            assert body and body.strip(), \
                f"{c.code}/{s.code}: missing {c.default_lang} body"
            assert isinstance(s.volatile, bool)


def test_scopes_resolve_to_real_regions_and_permits():
    for c in WITH_PATH:
        for s in c.path:
            if s.region_scope:
                assert s.region_scope in c.regions, (c.code, s.region_scope)
            for code in s.permit_scope:
                assert code in c.permits, (c.code, code)


def test_manifest_ordered_and_serialisable():
    order = {code: i for i, code in enumerate(Country._PATH_ORDER)}
    for c in WITH_PATH:
        man = c.path_manifest()
        json.dumps(man)                                  # JSON-serialisable
        assert len(man) == len(c.path)                   # every wired step carried
        ranks = [order.get(s["code"], 99) for s in man]
        assert ranks == sorted(ranks), c.code            # road-to-the-permit order


def test_staleness_fingerprints_path():
    snap = staleness.snapshot(refresh=False)
    for c in WITH_PATH:
        key = f"path:{c.code}"
        assert key in snap, key
        assert snap[key]["grade"] == "reference"         # advisory, not CI-fatal
        assert snap[key]["digest"]
    # Deterministic: a second snapshot fingerprints the path identically (no
    # timestamps or ordering leaking in) — required for the lock to be stable.
    again = staleness.snapshot(refresh=False)
    pick = lambda d: {k: v for k, v in d.items() if k.startswith("path:")}
    assert pick(again) == pick(snap)


def test_docs_in_sync_with_data():
    import run
    docs = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "docs")
    for code in ("CH", "DE", "FR"):
        path = os.path.join(docs, run._PATH_DOC_FILE[code])
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        assert run._PATH_DOC_START in text and run._PATH_DOC_END in text, code
        block = text[text.index(run._PATH_DOC_START):text.index(run._PATH_DOC_END)]
        assert run._path_doc_section(code) in block, \
            f"docs/{run._PATH_DOC_FILE[code]} out of sync — run `python run.py path-docs`"


if __name__ == "__main__":
    for _name, _fn in sorted(globals().items()):
        if _name.startswith("test_") and callable(_fn):
            _fn()
            print("ok", _name)
