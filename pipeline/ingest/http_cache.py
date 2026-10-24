"""Cached HTTP helper shared by every ingest client. TEAMMATE-owned.

Cache-on-first-pull: a GET is keyed by (source, url+params). On a hit we return the
stored JSON and never touch the network, so the demo runs offline. On a miss we fetch
with polite rate-limiting + retry, store the body, and return it.

Two controls sit on top of that:
  * TTL — pass `ttl_seconds` to treat a cache entry older than that as stale and
    refetch it (when online). The default `None` never expires, matching the
    cache-on-first-pull behaviour the demo relies on.
  * Offline mode — set `offline=True` (or the `INGEST_OFFLINE` env var) to guarantee
    no network call: a hit is returned regardless of age, and a miss raises
    `OfflineCacheMiss` instead of fetching. This makes a live demo independent of the
    network once the cache/seed is populated.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from database import get_db

# Env values that count as "on" for INGEST_OFFLINE.
_TRUTHY = {"1", "true", "yes", "on"}


class OfflineCacheMiss(RuntimeError):
    """Raised when offline mode is on but the request isn't in the cache/seed."""


# Params that carry credentials or the polite-pool contact. They must NOT appear in the
# cache key: the key should identify the logical request, so a seed built keyless is a hit
# whether or not a key is set, and no secret ever lands in a committed seed's request_key.
_AUTH_PARAMS = frozenset({"api_key", "mailto", "email"})


def _request_key(url: str, params: dict[str, Any] | None) -> str:
    items = sorted(
        (k, v) for k, v in (params or {}).items() if k not in _AUTH_PARAMS
    )
    return url + "?" + "&".join(f"{k}={v}" for k, v in items)


def _is_offline(offline: bool | None) -> bool:
    """Resolve offline mode: explicit arg wins, else the INGEST_OFFLINE env var."""
    if offline is not None:
        return offline
    return os.environ.get("INGEST_OFFLINE", "").strip().lower() in _TRUTHY


def _is_stale(fetched_at: str, ttl_seconds: float | None) -> bool:
    """True if a cache entry is older than `ttl_seconds`. `None` TTL never expires."""
    if ttl_seconds is None:
        return False
    try:
        ts = datetime.fromisoformat(fetched_at)
    except (TypeError, ValueError):
        # Unparseable timestamp -> treat as stale so we refetch rather than trust it.
        return True
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    age = (datetime.now(timezone.utc) - ts).total_seconds()
    return age > ttl_seconds


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, max=8))
def _fetch(url: str, params: dict[str, Any] | None, headers: dict[str, str] | None) -> httpx.Response:
    resp = httpx.get(url, params=params, headers=headers, timeout=30.0)
    resp.raise_for_status()
    return resp


def cached_get_json(
    source: str,
    url: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    force_refresh: bool = False,
    ttl_seconds: float | None = None,
    offline: bool | None = None,
) -> Any:
    """Return parsed JSON for a GET, reading/writing the api_cache table.

    Args:
        source: cache namespace, e.g. 'openalex' | 'pubmed' | 'chembl'.
        url, params, headers: the request.
        force_refresh: ignore any cached entry and refetch (online only).
        ttl_seconds: treat a cached entry older than this as stale and refetch it
            when online. `None` (default) never expires.
        offline: force offline mode. When omitted, falls back to the INGEST_OFFLINE
            env var. In offline mode a hit is always returned and a miss raises
            `OfflineCacheMiss` — the network is never touched.
    """
    db = get_db()
    key = _request_key(url, params)
    is_offline = _is_offline(offline)

    # --- offline mode: cache/seed only, never the network ---
    if is_offline:
        hit = db.cache_get_meta(source, key)
        if hit is not None:
            return hit[0]
        raise OfflineCacheMiss(
            f"offline mode is on and no cached response for source={source!r} "
            f"key={key!r}. Seed the cache (scripts/seed_cache.py) or run online."
        )

    # --- online: honour force_refresh and TTL ---
    if not force_refresh:
        hit = db.cache_get_meta(source, key)
        if hit is not None:
            body, fetched_at = hit
            if not _is_stale(fetched_at, ttl_seconds):
                return body
            # stale -> fall through and refetch below

    contact = os.environ.get("CONTACT_EMAIL")
    hdrs = dict(headers or {})
    if contact and "User-Agent" not in hdrs:
        hdrs["User-Agent"] = f"HackachusettsHealth/0.1 (mailto:{contact})"

    resp = _fetch(url, params, hdrs)
    body = resp.json()
    db.cache_put(source, key, body, status_code=resp.status_code)
    return body
