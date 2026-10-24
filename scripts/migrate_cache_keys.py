"""One-time migration: strip api_key / mailto from existing api_cache request_keys.

The cache key used to include api_key and mailto, so a keyed call and a keyless call for
the same data stored two rows. http_cache now excludes those params; this rewrites
existing rows to the stripped key so nothing is re-downloaded.

    python scripts/migrate_cache_keys.py

Idempotent: safe to run more than once. On a key collision (two old rows map to the same
stripped key) we keep the most recently fetched row.

IMPORTANT: the rewritten key must match http_cache._request_key byte-for-byte (raw,
not URL-encoded), or the app will miss the cache and re-download everything.
"""

from __future__ import annotations

import sqlite3
from urllib.parse import unquote

from database.db import _db_path
from pipeline.ingest.http_cache import _CACHE_KEY_EXCLUDE


def _strip(request_key: str) -> str:
    """Rebuild the key in the app's raw format, dropping excluded params.

    Values are URL-decoded so a previously over-encoded key (%3A, %2C, %2A) is restored
    to the raw form http_cache._request_key uses. Idempotent on already-raw keys.
    """
    if "?" not in request_key:
        return request_key
    base, qs = request_key.split("?", 1)
    pairs = []
    for part in qs.split("&"):
        if not part:
            continue
        k, _, v = part.partition("=")
        k = unquote(k)
        if k in _CACHE_KEY_EXCLUDE:
            continue
        pairs.append((k, unquote(v)))
    pairs.sort()
    return base + "?" + "&".join(f"{k}={v}" for k, v in pairs)


def main() -> int:
    conn = sqlite3.connect(str(_db_path()))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT rowid, source, request_key, fetched_at FROM api_cache"
    ).fetchall()

    changed = 0
    for r in rows:
        new_key = _strip(r["request_key"])
        if new_key == r["request_key"]:
            continue
        # does a row with the stripped key already exist?
        existing = conn.execute(
            "SELECT fetched_at FROM api_cache WHERE source=? AND request_key=?",
            (r["source"], new_key),
        ).fetchone()
        if existing is None:
            conn.execute(
                "UPDATE api_cache SET request_key=? WHERE rowid=?", (new_key, r["rowid"])
            )
            changed += 1
        else:
            # keep the newer of the two, drop the old-keyed duplicate
            if r["fetched_at"] > existing["fetched_at"]:
                conn.execute(
                    "UPDATE api_cache SET response=(SELECT response FROM api_cache WHERE rowid=?),"
                    " status_code=(SELECT status_code FROM api_cache WHERE rowid=?),"
                    " fetched_at=? WHERE source=? AND request_key=?",
                    (r["rowid"], r["rowid"], r["fetched_at"], r["source"], new_key),
                )
            conn.execute("DELETE FROM api_cache WHERE rowid=?", (r["rowid"],))
            changed += 1
    conn.commit()
    total = conn.execute("SELECT count(*) FROM api_cache").fetchone()[0]
    conn.close()
    print(f"Migrated {changed} rows. api_cache now has {total} rows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
