"""Load local environment configuration (API keys, contact email) from `.env`.

Keys are OPTIONAL — every source works keyless at lower rate limits (see .env.example):
  * OPENALEX_API_KEY  -> OpenAlex higher rate limit / daily budget
  * NCBI_API_KEY      -> PubMed/NCBI 10 req/s instead of 3
  * CONTACT_EMAIL     -> OpenAlex/NCBI "polite pool" (recommended even without keys)

Nothing is hardcoded here. Real values live in a local, gitignored `.env` file; this
module just loads that file into the process environment so the ingest clients can read
it via os.environ. `load_env()` is idempotent and never overrides values already set in
the real environment (so an explicit `VAR=... python ...` still wins).
"""

from __future__ import annotations

import os
from pathlib import Path

# repo root = three levels up from this file (pipeline/ingest/env.py)
_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"

_loaded = False


def load_env(path: str | Path | None = None, override: bool = False) -> bool:
    """Load `.env` into os.environ once. Returns True if a file was loaded.

    Existing environment variables are preserved unless `override=True`. Safe to call
    repeatedly; only the first successful load does work.
    """
    global _loaded
    if _loaded and path is None:
        return True

    env_path = Path(path) if path else _ENV_PATH
    if not env_path.is_file():
        if path is None:
            _loaded = True  # nothing to load, don't retry every call
        return False

    try:
        from dotenv import load_dotenv
    except ImportError:
        # python-dotenv is a declared dependency; if it's somehow absent, fall back to
        # a minimal parser so keys in .env still work.
        _load_env_fallback(env_path, override)
    else:
        load_dotenv(env_path, override=override)

    if path is None:
        _loaded = True
    return True


def _load_env_fallback(env_path: Path, override: bool) -> None:
    """Minimal KEY=VALUE parser used only if python-dotenv isn't importable."""
    for raw in env_path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and (override or key not in os.environ):
            os.environ[key] = value
