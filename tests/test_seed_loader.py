"""Tests for the offline cache seed loader (Task 3)."""

from __future__ import annotations

import json

import pytest

import database.db as dbmod
import pipeline.ingest.http_cache as hc
from database.db import Database


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    db = Database(tmp_path / "test.db")
    monkeypatch.setattr(dbmod, "_singleton", db, raising=False)
    yield db
    db.close()


def _write_seed(dir_, source, records):
    dir_.mkdir(parents=True, exist_ok=True)
    (dir_ / f"{source}.json").write_text(json.dumps(records))


def test_load_seed_populates_cache(temp_db, tmp_path):
    seed = tmp_path / "seed"
    _write_seed(seed, "openalex", [
        {"request_key": "k1", "response": {"a": 1}, "status_code": 200},
        {"request_key": "k2", "response": {"b": 2}},
    ])
    n = temp_db.load_seed(seed)
    assert n == 2
    assert temp_db.cache_get("openalex", "k1") == {"a": 1}
    assert temp_db.cache_get("openalex", "k2") == {"b": 2}


def test_seeded_entry_is_an_offline_cache_hit(temp_db, tmp_path, monkeypatch):
    seed = tmp_path / "seed"
    key = hc._request_key("http://api/x", {"q": "z"})
    _write_seed(seed, "pubmed", [{"request_key": key, "response": {"seeded": True}}])
    temp_db.load_seed(seed)

    # Any accidental fetch would blow up this test.
    def boom(*a, **k):
        raise AssertionError("network must not be touched")

    monkeypatch.setattr(hc, "_fetch", boom)
    out = hc.cached_get_json("pubmed", "http://api/x", params={"q": "z"}, offline=True)
    assert out == {"seeded": True}


def test_load_seed_is_idempotent(temp_db, tmp_path):
    seed = tmp_path / "seed"
    _write_seed(seed, "chembl", [{"request_key": "k", "response": {"v": 1}}])
    assert temp_db.load_seed(seed) == 1
    assert temp_db.load_seed(seed) == 1  # upsert, no duplicate rows/errors
    assert temp_db.cache_get("chembl", "k") == {"v": 1}


def test_load_seed_missing_dir_is_noop(temp_db, tmp_path):
    assert temp_db.load_seed(tmp_path / "does-not-exist") == 0


def test_load_seed_skips_malformed_records(temp_db, tmp_path):
    seed = tmp_path / "seed"
    _write_seed(seed, "openalex", [
        {"request_key": "good", "response": {"ok": True}},
        {"no_request_key": True},   # skipped
        "garbage",                  # skipped
    ])
    assert temp_db.load_seed(seed) == 1
    assert temp_db.cache_get("openalex", "good") == {"ok": True}


def test_committed_seed_loads(temp_db, monkeypatch):
    """The real database/seed/ files load and parse via the clients offline."""
    monkeypatch.setenv("INGEST_OFFLINE", "1")  # guarantee no network even on a miss
    n = temp_db.load_seed()  # default dir = database/seed
    assert n >= 1
    # the committed OpenAlex works entry should normalize through the parser. The seed
    # is self-consistent: the topic search returns T10159 and the works entry is keyed
    # to that same id, so this is an offline cache hit.
    from pipeline.ingest import openalex
    counts = openalex.works_by_year("https://openalex.org/T10159", 2015, 2024)
    assert counts and counts[0]["year"] == 2015
