"""OpenAlex ingest: yearly publication counts per topic + topic search. TEAMMATE-owned.

Keyless: ~10 req/s and a tenth of the daily budget. With a free key: 30 req/s, ~$1/day
(~10,000 list calls or ~1,000 searches). We cache every response so repeated demo runs
cost nothing.

Parsing is split from fetching: the `_parse_*` helpers turn a raw OpenAlex JSON body
into clean, predictable records and fail soft (skip malformed rows, return empty on a
missing/odd response) so a bad payload never crashes the pipeline.
"""

from __future__ import annotations

import os
from typing import Any

from pipeline.ingest.http_cache import cached_get_json

_BASE = "https://api.openalex.org"


def _auth_params() -> dict[str, str]:
    params: dict[str, str] = {}
    key = os.environ.get("OPENALEX_API_KEY")
    email = os.environ.get("CONTACT_EMAIL")
    if key:
        params["api_key"] = key
    if email:
        params["mailto"] = email
    return params


def _parse_topics(body: Any) -> list[dict]:
    """Normalise a /topics response into [{id, display_name, works_count}]."""
    if not isinstance(body, dict):
        return []
    out: list[dict] = []
    for r in body.get("results", []) or []:
        if not isinstance(r, dict):
            continue
        tid = r.get("id")
        if not tid:
            continue
        try:
            works = int(r.get("works_count", 0) or 0)
        except (TypeError, ValueError):
            works = 0
        out.append({
            "id": tid,
            "display_name": r.get("display_name") or "",
            "works_count": works,
        })
    return out


def _parse_works_by_year(body: Any) -> list[dict]:
    """Normalise a grouped /works response into sorted [{year:int, works:int}]."""
    if not isinstance(body, dict):
        return []
    out: list[dict] = []
    for g in body.get("group_by", []) or []:
        if not isinstance(g, dict):
            continue
        try:
            out.append({"year": int(g["key"]), "works": int(g["count"])})
        except (KeyError, TypeError, ValueError):
            continue
    return sorted(out, key=lambda r: r["year"])


def search_topics(query: str, per_page: int = 10) -> list[dict]:
    """Search OpenAlex topics by name. Returns [{id, display_name, works_count}, ...]."""
    params = {"search": query, "per-page": per_page, **_auth_params()}
    body = cached_get_json("openalex", f"{_BASE}/topics", params=params)
    return _parse_topics(body)


def works_by_year(topic_id: str, from_year: int = 2015, to_year: int = 2024) -> list[dict]:
    """Yearly works count for a topic id, as sorted [{year, works}]."""
    short_id = topic_id.rsplit("/", 1)[-1]
    params = {
        "filter": f"topics.id:{short_id},from_publication_date:{from_year}-01-01,"
                  f"to_publication_date:{to_year}-12-31",
        "group_by": "publication_year",
        **_auth_params(),
    }
    body = cached_get_json("openalex", f"{_BASE}/works", params=params)
    return _parse_works_by_year(body)
