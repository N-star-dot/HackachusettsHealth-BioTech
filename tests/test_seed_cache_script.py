"""Tests for scripts/seed_cache.py export logic (Task 4). No network is used."""

from __future__ import annotations

import json

import pytest

import database.db as dbmod
from database.db import Database
from scripts import seed_cache


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    db = Database(tmp_path / "test.db")
    monkeypatch.setattr(dbmod, "_singleton", db, raising=False)
    yield db
    db.close()


def test_cache_all_returns_parsed_rows(temp_db):
    temp_db.cache_put("openalex", "k1", {"a": 1})
    temp_db.cache_put("pubmed", "k2", {"b": 2})
    all_rows = temp_db.cache_all()
    assert len(all_rows) == 2
    oa = temp_db.cache_all("openalex")
    assert oa == [{"source": "openalex", "request_key": "k1",
                   "response": {"a": 1}, "status_code": 200}]


def test_export_writes_seed_files(temp_db, tmp_path):
    temp_db.cache_put("openalex", "oa-key", {"group_by": [{"key": "2020", "count": 10}]})
    temp_db.cache_put("chembl", "ch-key", {"activities": []})
    seed_dir = tmp_path / "seed"

    total = seed_cache.export_seed(seed_dir)
    assert total == 2

    oa = json.loads((seed_dir / "openalex.json").read_text())
    assert oa[0]["request_key"] == "oa-key"
    assert oa[0]["status_code"] == 200
    # pubmed had no rows -> empty list file still written
    assert json.loads((seed_dir / "pubmed.json").read_text()) == []


def test_export_roundtrips_through_load_seed(temp_db, tmp_path):
    temp_db.cache_put("openalex", "rt-key", {"hello": "world"})
    seed_dir = tmp_path / "seed"
    seed_cache.export_seed(seed_dir)

    # fresh DB loads the exported seed and sees the same value
    fresh = Database(tmp_path / "fresh.db")
    n = fresh.load_seed(seed_dir)
    assert n >= 1
    assert fresh.cache_get("openalex", "rt-key") == {"hello": "world"}
    fresh.close()
