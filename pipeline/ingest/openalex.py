"""OpenAlex ingest: yearly publication counts per topic + topic search. TEAMMATE-owned.

Keyless: ~10 req/s and a tenth of the daily budget. With a free key: 30 req/s, ~$1/day
(~10,000 list calls or ~1,000 searches). We cache every response so repeated demo runs
cost nothing.
"""

from __future__ import annotations

import os

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


def search_topics(query: str, per_page: int = 10) -> list[dict]:
    """Search OpenAlex topics by name. Returns [{id, display_name, works_count}, ...]."""
    params = {"search": query, "per-page": per_page, **_auth_params()}
    body = cached_get_json("openalex", f"{_BASE}/topics", params=params)
    return body.get("results", [])


# OpenAlex domain ids for the life/health sciences (the model's universe).
LIFE_SCIENCE_DOMAINS: tuple[int, ...] = (1, 4)  # 1 = Life Sciences, 4 = Health Sciences


def enumerate_topics_by_domain(
    domain_id: int, per_page: int = 200, max_topics: int | None = None
) -> list[dict]:
    """Page through all topics in an OpenAlex domain, sorted by works_count desc.

    Returns a list of {openalex_id, name, field, works_count}. Uses cursor paging so it
    reliably walks the full set. Every page response is cached.
    """
    results: list[dict] = []
    cursor = "*"
    while cursor:
        params = {
            "filter": f"domain.id:domains/{domain_id}",
            "sort": "works_count:desc",
            "per-page": per_page,
            "cursor": cursor,
            **_auth_params(),
        }
        body = cached_get_json("openalex", f"{_BASE}/topics", params=params)
        for t in body.get("results", []):
            field = (t.get("field") or {}).get("display_name")
            results.append(
                {
                    "openalex_id": t["id"].rsplit("/", 1)[-1],
                    "name": t.get("display_name"),
                    "field": field,
                    "works_count": t.get("works_count", 0),
                }
            )
            if max_topics and len(results) >= max_topics:
                return results
        cursor = body.get("meta", {}).get("next_cursor")
    return results


def enumerate_life_science_topics(max_topics: int | None = None) -> list[dict]:
    """All topics across the life- and health-science domains (deduped by id)."""
    seen: dict[str, dict] = {}
    for domain_id in LIFE_SCIENCE_DOMAINS:
        for t in enumerate_topics_by_domain(domain_id):
            seen.setdefault(t["openalex_id"], t)
            if max_topics and len(seen) >= max_topics:
                return list(seen.values())
    return list(seen.values())


def works_by_year(topic_id: str, from_year: int = 2015, to_year: int = 2024) -> list[dict]:
    """Yearly works count for a topic id, as [{year, works}]."""
    short_id = topic_id.rsplit("/", 1)[-1]
    params = {
        "filter": f"topics.id:{short_id},from_publication_date:{from_year}-01-01,"
                  f"to_publication_date:{to_year}-12-31",
        "group_by": "publication_year",
        **_auth_params(),
    }
    body = cached_get_json("openalex", f"{_BASE}/works", params=params)
    out = []
    for g in body.get("group_by", []):
        try:
            out.append({"year": int(g["key"]), "works": int(g["count"])})
        except (KeyError, ValueError):
            continue
    return sorted(out, key=lambda r: r["year"])
