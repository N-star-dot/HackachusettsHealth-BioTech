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


def search_works_group_by_topic(query: str, per_page: int = 10) -> list[dict]:
    """Resolve a natural-language query to topics by searching WORKS and grouping them by
    primary_topic. This matches questions like "JAK inhibitors in autoimmune disease" that
    the /topics name search misses. Returns the top groups as
    [{topic_id, name, count}, ...] sorted by work count (OpenAlex already sorts desc)."""
    params = {"search": query, "group_by": "primary_topic.id",
              "per-page": per_page, **_auth_params()}
    body = cached_get_json("openalex", f"{_BASE}/works", params=params)
    out: list[dict] = []
    for g in body.get("group_by", []):
        key = g.get("key") or ""
        tid = key.rsplit("/", 1)[-1]
        if not tid.startswith("T"):
            continue
        out.append({
            "topic_id": tid,
            "name": g.get("key_display_name"),
            "count": int(g.get("count", 0)),
        })
    return out


def topic_meta(topic_id: str) -> dict:
    """Fetch a topic's metadata ({field, subfield, display_name}) by id (cached)."""
    short = topic_id.rsplit("/", 1)[-1]
    body = cached_get_json("openalex", f"{_BASE}/topics/{short}")
    return {
        "openalex_id": short,
        "name": body.get("display_name"),
        "field": (body.get("field") or {}).get("display_name"),
        "subfield_id": (body.get("subfield") or {}).get("id"),
    }


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


def sibling_topics(subfield_id: str, per_page: int = 50) -> list[dict]:
    """List topics in a subfield (cached). Returns [{openalex_id, name, field}]."""
    short = subfield_id.rsplit("/", 1)[-1]
    params = {
        "filter": f"subfield.id:subfields/{short}",
        "per-page": per_page,
        "sort": "works_count:desc",
        **_auth_params(),
    }
    body = cached_get_json("openalex", f"{_BASE}/topics", params=params)
    out = []
    for t in body.get("results", []):
        out.append({
            "openalex_id": t["id"].rsplit("/", 1)[-1],
            "name": t.get("display_name"),
            "field": (t.get("field") or {}).get("display_name"),
        })
    return out


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
