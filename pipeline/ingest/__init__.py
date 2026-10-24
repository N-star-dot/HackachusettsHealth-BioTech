"""Data ingestion: OpenAlex, PubMed, ChEMBL. Every response cached on first pull.

The demo runs offline once the cache is warm. See http_cache.cached_get_json.
"""

from pipeline.ingest import chembl, openalex, pubmed
from pipeline.ingest.http_cache import cached_get_json

__all__ = ["openalex", "pubmed", "chembl", "cached_get_json"]
