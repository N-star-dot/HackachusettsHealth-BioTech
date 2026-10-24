"""Cached HTTP helper shared by every ingest client. TEAMMATE-owned.

Cache-on-first-pull: a GET is keyed by (source, url+params). On a hit we return the
stored JSON and never touch the network, so the demo runs offline. On a miss we fetch
with polite rate-limiting + retry, store the body, and return it.
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from database import get_db


# Params that must NOT affect the cache key: they're per-user auth / politeness and
# don't change the response body. Stripping them means a keyed and a keyless call for
# the same data share one cache row.
_CACHE_KEY_EXCLUDE = frozenset({"api_key", "mailto"})


def _request_key(url: str, params: dict[str, Any] | None) -> str:
    items = sorted((k, v) for k, v in (params or {}).items() if k not in _CACHE_KEY_EXCLUDE)
    return url + "?" + "&".join(f"{k}={v}" for k, v in items)


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
) -> Any:
    """Return parsed JSON for a GET, reading/writing the api_cache table."""
    db = get_db()
    key = _request_key(url, params)

    if not force_refresh:
        hit = db.cache_get(source, key)
        if hit is not None:
            return hit

    contact = os.environ.get("CONTACT_EMAIL")
    hdrs = dict(headers or {})
    if contact and "User-Agent" not in hdrs:
        hdrs["User-Agent"] = f"HackachusettsHealth/0.1 (mailto:{contact})"

    resp = _fetch(url, params, hdrs)
    body = resp.json()
    db.cache_put(source, key, body, status_code=resp.status_code)
    return body
