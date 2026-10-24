"""Tests for the ingest cache layer: TTL + offline mode (Task 1).

No real network is used — `_fetch` is monkeypatched. Each test runs against a fresh
temp SQLite DB by resetting the `database.db` singleton.
"""

from __future__ import annotations

import pytest

import database.db as dbmod
import pipeline.ingest.http_cache as hc
from database.db import Database


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Point the process-wide db singleton at a throwaway SQLite file."""
    db = Database(tmp_path / "test.db")
    monkeypatch.setattr(dbmod, "_singleton", db, raising=False)
    yield db
    db.close()


@pytest.fixture
def no_network(monkeypatch):
    """Make any accidental network call fail loudly, and count intended fetches."""
    calls = {"n": 0}

    class _Resp:
        status_code = 200

        def __init__(self, body):
            self._body = body

        def json(self):
            return self._body

    def fake_fetch(url, params, headers):
        calls["n"] += 1
        return _Resp({"fetched": True, "url": url, "n": calls["n"]})

    monkeypatch.setattr(hc, "_fetch", fake_fetch)
    return calls


def test_fresh_hit_returns_without_network(temp_db, no_network):
    temp_db.cache_put("openalex", hc._request_key("http://x", {"a": 1}), {"cached": True})
    out = hc.cached_get_json("openalex", "http://x", params={"a": 1})
    assert out == {"cached": True}
    assert no_network["n"] == 0  # cache hit -> no fetch


def test_miss_online_fetches_and_caches(temp_db, no_network):
    out = hc.cached_get_json("openalex", "http://x", params={"a": 2})
    assert out["fetched"] is True
    assert no_network["n"] == 1
    # second call is now a hit -> still only one fetch total
    again = hc.cached_get_json("openalex", "http://x", params={"a": 2})
    assert again["fetched"] is True
    assert no_network["n"] == 1


def test_stale_hit_refetches_when_online(temp_db, no_network, monkeypatch):
    key = hc._request_key("http://x", {"a": 3})
    temp_db.cache_put("openalex", key, {"old": True})
    # force the stored entry to look old by making _is_stale report True
    monkeypatch.setattr(hc, "_is_stale", lambda fetched_at, ttl: True)
    out = hc.cached_get_json("openalex", "http://x", params={"a": 3}, ttl_seconds=1)
    assert out["fetched"] is True  # refetched, not the stale {"old": True}
    assert no_network["n"] == 1


def test_fresh_within_ttl_not_refetched(temp_db, no_network, monkeypatch):
    key = hc._request_key("http://x", {"a": 4})
    temp_db.cache_put("openalex", key, {"old": True})
    monkeypatch.setattr(hc, "_is_stale", lambda fetched_at, ttl: False)
    out = hc.cached_get_json("openalex", "http://x", params={"a": 4}, ttl_seconds=999999)
    assert out == {"old": True}
    assert no_network["n"] == 0


def test_offline_hit_returns_regardless_of_age(temp_db, no_network):
    key = hc._request_key("http://x", {"a": 5})
    temp_db.cache_put("openalex", key, {"seeded": True})
    out = hc.cached_get_json("openalex", "http://x", params={"a": 5}, offline=True)
    assert out == {"seeded": True}
    assert no_network["n"] == 0


def test_offline_miss_raises(temp_db, no_network):
    with pytest.raises(hc.OfflineCacheMiss):
        hc.cached_get_json("openalex", "http://x", params={"a": 6}, offline=True)
    assert no_network["n"] == 0  # never touched the network


def test_offline_resolved_from_env(temp_db, no_network, monkeypatch):
    monkeypatch.setenv("INGEST_OFFLINE", "1")
    with pytest.raises(hc.OfflineCacheMiss):
        hc.cached_get_json("openalex", "http://x", params={"a": 7})
    assert no_network["n"] == 0


def test_is_stale_helper():
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    old = (now - timedelta(seconds=120)).isoformat(timespec="seconds")
    recent = now.isoformat(timespec="seconds")
    assert hc._is_stale(old, ttl_seconds=60) is True
    assert hc._is_stale(recent, ttl_seconds=60) is False
    assert hc._is_stale(old, ttl_seconds=None) is False  # None never expires
    assert hc._is_stale("not-a-date", ttl_seconds=60) is True  # unparseable -> stale


def test_request_key_ignores_auth_params():
    """Auth/polite-pool params must not change the cache key, so a keyless seed is a
    hit whether or not a key is configured (and no secret lands in a seed key)."""
    base = hc._request_key("http://api/x", {"q": "z"})
    with_key = hc._request_key(
        "http://api/x", {"q": "z", "api_key": "secret", "mailto": "me@x.com", "email": "me@x.com"}
    )
    assert base == with_key
    assert "secret" not in with_key
