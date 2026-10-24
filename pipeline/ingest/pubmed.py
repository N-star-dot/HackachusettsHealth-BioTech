"""PubMed (NCBI E-utilities) ingest: PMID search, titles, and ABSTRACTS. Owner B.

Free: 3 req/s keyless, 10 req/s with a free key. Every response cached so the demo
replays offline.

Abstracts are the evidence the Designer reads and the checker verifies against, so we
fetch them with a batched EFetch (XML), parse ArticleTitle + every AbstractText (joining
labeled sections as "LABEL: text"), and normalise the stored text exactly the way the
checker normalises quotes (NFKC + collapsed whitespace) so comparisons are stable.
"""

from __future__ import annotations

import os
import re
import unicodedata
import xml.etree.ElementTree as ET

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


def normalise_abstract(text: str) -> str:
    """NFKC + collapsed whitespace. Stored exactly like this so the checker's _normalise
    (which also lowercases at check time) matches."""
    text = unicodedata.normalize("NFKC", text or "")
    return re.sub(r"\s+", " ", text).strip()


def fetch_title(pmid: str) -> str | None:
    """Article title for a PMID, or None if it doesn't resolve."""
    params = {"db": "pubmed", "id": pmid, "retmode": "json", **_key_params()}
    body = cached_get_json("pubmed", f"{_BASE}/esummary.fcgi", params=params)
    record = body.get("result", {}).get(pmid)
    if not record or record.get("error"):
        return None
    return record.get("title")


def search(query: str, retmax: int = 5) -> list[str]:
    """PMIDs for a query (most relevant first)."""
    params = {"db": "pubmed", "term": query, "retmode": "json", "retmax": retmax, **_key_params()}
    body = cached_get_json("pubmed", f"{_BASE}/esearch.fcgi", params=params)
    return body.get("esearchresult", {}).get("idlist", [])


def _cached_get_xml(url: str, params: dict) -> str:
    """GET returning XML text, cached in api_cache (stored as a JSON string value).

    http_cache only has a JSON variant, so we cache the raw XML text here via the DB
    directly — same cache table, keyed identically (api_key/mailto excluded)."""
    db = get_db()
    key = _request_key(url, params)
    hit = db.cache_get("pubmed", key)
    if hit is not None:
        return hit  # stored as a plain string
    contact = os.environ.get("CONTACT_EMAIL")
    headers = {"User-Agent": f"HackachusettsHealth/0.1 (mailto:{contact})"} if contact else None
    resp = _fetch(url, params, headers)
    text = resp.text
    db.cache_put("pubmed", key, text, status_code=resp.status_code)
    return text


def _parse_articles(xml_text: str) -> dict[str, dict]:
    """Parse EFetch XML -> {pmid: {pmid, title, abstract}}.

    Joins labeled AbstractText sections as "LABEL: text". Returns normalised abstract
    text. Articles with no abstract are omitted (caller drops them)."""
    out: dict[str, dict] = {}
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return out
    for art in root.findall(".//PubmedArticle"):
        pmid = art.findtext(".//PMID")
        if not pmid:
            continue
        title = art.findtext(".//ArticleTitle") or ""
        pieces: list[str] = []
        for ab in art.findall(".//Abstract/AbstractText"):
            txt = "".join(ab.itertext()).strip()
            if not txt:
                continue
            label = ab.get("Label")
            pieces.append(f"{label}: {txt}" if label else txt)
        if not pieces:
            continue  # no abstract -> useless as evidence
        out[pmid] = {
            "pmid": pmid,
            "title": normalise_abstract(title),
            "abstract": normalise_abstract(" ".join(pieces)),
        }
    return out


def fetch_abstracts(pmids: list[str]) -> dict[str, dict]:
    """One batched EFetch for a list of PMIDs -> {pmid: {pmid, title, abstract}}.

    Papers without an abstract are dropped. Cached (offline-replayable)."""
    pmids = [str(p) for p in pmids if p]
    if not pmids:
        return {}
    params = {"db": "pubmed", "id": ",".join(pmids), "retmode": "xml", **_key_params()}
    xml_text = _cached_get_xml(f"{_BASE}/efetch.fcgi", params)
    return _parse_articles(xml_text)
