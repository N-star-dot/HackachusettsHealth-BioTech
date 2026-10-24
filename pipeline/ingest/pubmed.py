"""PubMed (NCBI E-utilities) ingest: abstracts for the Designer + PMID checks.

Free: 3 req/s keyless, 10 req/s with a free key. Cached on first pull.
"""

from __future__ import annotations

import os

from pipeline.ingest.http_cache import cached_get_json

_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def _key_params() -> dict[str, str]:
    params: dict[str, str] = {}
    key = os.environ.get("NCBI_API_KEY")
    email = os.environ.get("CONTACT_EMAIL")
    if key:
        params["api_key"] = key
    if email:
        params["email"] = email
    return params


def fetch_title(pmid: str) -> str | None:
    """Return the article title for a PMID, or None if it doesn't resolve.
    Used by the stage-2 citation checker."""
    params = {"db": "pubmed", "id": pmid, "retmode": "json", **_key_params()}
    body = cached_get_json("pubmed", f"{_BASE}/esummary.fcgi", params=params)
    result = body.get("result", {})
    record = result.get(pmid)
    if not record or record.get("error"):
        return None
    return record.get("title")


def search(query: str, retmax: int = 5) -> list[str]:
    """Return a list of PMIDs for a query (most relevant first)."""
    params = {"db": "pubmed", "term": query, "retmode": "json", "retmax": retmax, **_key_params()}
    body = cached_get_json("pubmed", f"{_BASE}/esearch.fcgi", params=params)
    return body.get("esearchresult", {}).get("idlist", [])
