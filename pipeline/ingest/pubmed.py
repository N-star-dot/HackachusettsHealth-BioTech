"""PubMed (NCBI E-utilities) ingest: PMID search, titles, and ABSTRACTS. Owner B.

Free: 3 req/s keyless, 10 req/s with a free key. Cached on first pull.

Parsing is split from fetching: the `_parse_*` helpers turn a raw E-utilities JSON body
into clean values and fail soft (a missing/error record yields None or []), so a bad or
partial response never crashes the citation checker.
"""

from __future__ import annotations

import os
from typing import Any

from database import get_db
from pipeline.ingest.http_cache import _fetch, _request_key, cached_get_json

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


def _parse_title(body: Any, pmid: str) -> str | None:
    """Pull the title for a PMID out of an esummary response, or None."""
    if not isinstance(body, dict):
        return None
    result = body.get("result")
    if not isinstance(result, dict):
        return None
    record = result.get(pmid)
    if not isinstance(record, dict) or record.get("error"):
        return None
    title = record.get("title")
    return title if isinstance(title, str) and title else None


def _parse_pmids(body: Any) -> list[str]:
    """Pull the PMID list out of an esearch response, de-duped, order preserved."""
    if not isinstance(body, dict):
        return []
    idlist = body.get("esearchresult", {}).get("idlist", []) if isinstance(
        body.get("esearchresult"), dict
    ) else []
    seen: set[str] = set()
    out: list[str] = []
    for pid in idlist or []:
        pid = str(pid)
        if pid and pid not in seen:
            seen.add(pid)
            out.append(pid)
    return out


def fetch_title(pmid: str) -> str | None:
    """Article title for a PMID, or None if it doesn't resolve."""
    params = {"db": "pubmed", "id": pmid, "retmode": "json", **_key_params()}
    body = cached_get_json("pubmed", f"{_BASE}/esummary.fcgi", params=params)
    return _parse_title(body, pmid)


def search(query: str, retmax: int = 5) -> list[str]:
    """Return a list of PMIDs for a query (most relevant first), de-duped."""
    params = {"db": "pubmed", "term": query, "retmode": "json", "retmax": retmax, **_key_params()}
    body = cached_get_json("pubmed", f"{_BASE}/esearch.fcgi", params=params)
    return _parse_pmids(body)
