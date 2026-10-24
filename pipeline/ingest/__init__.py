"""Data ingestion: OpenAlex, PubMed, ChEMBL. Every response cached on first pull.

The demo runs offline once the cache is warm. See http_cache.cached_get_json.
"""

from pipeline.ingest.env import load_env

# Load a local .env (API keys, CONTACT_EMAIL) before any client reads os.environ.
# Keys are optional; this is a no-op when no .env is present.
load_env()

from pipeline.ingest import chembl, openalex, pubmed
from pipeline.ingest.http_cache import cached_get_json

__all__ = ["cached_get_json", "chembl", "load_env", "openalex", "pubmed"]
