"""SQLite access layer.

Thin, dependency-free wrapper over sqlite3. Two concerns:
  * api_cache  — the pipeline writes raw API responses here (cache-on-first-pull).
  * runs/reports — each stage persists its validated JSON contract here.

The connection is opened with a short busy_timeout and WAL mode (set in schema.sql)
so the parallel team can read/write concurrently without 'database is locked'.
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCHEMA_PATH = Path(__file__).with_name("schema.sql")
_DEFAULT_DB = Path(__file__).with_name("app.db")
_SEED_DIR = Path(__file__).with_name("seed")  # committed offline cache seed (JSON per source)


def _db_path() -> Path:
    return Path(os.environ.get("DATABASE_URL", str(_DEFAULT_DB)))


class Database:
    """Lightweight handle. Create once and share, or use `get_db()`.

    Each operation opens its own short-lived SQLite connection (WAL mode) rather than
    sharing one connection across threads. The async run worker and the GET /api/run
    poller run on different threads; sharing a single sqlite3 connection between them
    serialised and stalled reads (the "stuck at design" bug), because the poller's reads
    contended with the worker's writes on the same connection. Per-operation connections
    under WAL let readers and the writer proceed concurrently and safely.
    """

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else _db_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # B2.1: writes still serialise through one lock so two threads never write at once.
        self._write_lock = __import__("threading").Lock()
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        """A fresh connection for one operation. WAL + busy_timeout so a reader never
        blocks on a concurrent writer for more than the timeout."""
        conn = sqlite3.connect(str(self.path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 5000;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA_PATH.read_text())
            self._migrate(conn)
            conn.commit()

    def _migrate(self, conn: sqlite3.Connection) -> None:
        """Idempotent migrations for DBs created before a column was added."""
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(topic_features)")}
        if "growth" not in cols:
            conn.execute("ALTER TABLE topic_features ADD COLUMN growth REAL")
        cal_cols = {r["name"] for r in conn.execute("PRAGMA table_info(calibration_groups)")}
        if cal_cols and "document_ids" not in cal_cols:
            conn.execute(
                "ALTER TABLE calibration_groups ADD COLUMN document_ids TEXT NOT NULL DEFAULT '[]'"
            )
        run_cols = {r["name"] for r in conn.execute("PRAGMA table_info(runs)")}
        if "error" not in run_cols:
            conn.execute("ALTER TABLE runs ADD COLUMN error TEXT")

    # --- api cache ---------------------------------------------------------
    def cache_get(self, source: str, request_key: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT response FROM api_cache WHERE source=? AND request_key=?",
                (source, request_key),
            ).fetchone()
        return json.loads(row["response"]) if row else None

    def cache_get_meta(
        self, source: str, request_key: str
    ) -> tuple[Any, str] | None:
        """Like `cache_get` but also returns the stored `fetched_at` timestamp.

        Returns `(response, fetched_at)` or `None` on a miss. Used by the ingest
        cache layer to honour a TTL (compare `fetched_at` to now). `fetched_at` is
        the ISO-8601 UTC string written by `cache_put`.
        """
        row = self._conn.execute(
            "SELECT response, fetched_at FROM api_cache WHERE source=? AND request_key=?",
            (source, request_key),
        ).fetchone()
        if row is None:
            return None
        return json.loads(row["response"]), row["fetched_at"]

    def cache_put(
        self, source: str, request_key: str, response: Any, status_code: int = 200
    ) -> None:
        with self._write_lock, self._connect() as conn:
            conn.execute(
                """INSERT INTO api_cache(source, request_key, response, status_code, fetched_at)
                   VALUES(?,?,?,?,?)
                   ON CONFLICT(source, request_key) DO UPDATE SET
                     response=excluded.response,
                     status_code=excluded.status_code,
                     fetched_at=excluded.fetched_at""",
                (source, request_key, json.dumps(response), status_code, _now()),
            )
            conn.commit()

    def load_seed(self, seed_dir: str | Path | None = None) -> int:
        """Populate `api_cache` from committed seed files so the demo runs offline.

        Reads every `<source>.json` under `seed_dir` (default `database/seed/`). Each
        file is a JSON list of records: {"request_key", "response", "status_code"?}.
        The source name is taken from the file stem. Upserts via `cache_put`, so
        loading twice is a no-op. Missing dir or files => nothing loaded, no error.
        Returns the number of cache rows written.
        """
        directory = Path(seed_dir) if seed_dir else _SEED_DIR
        if not directory.is_dir():
            return 0
        loaded = 0
        for path in sorted(directory.glob("*.json")):
            source = path.stem
            try:
                records = json.loads(path.read_text())
            except (json.JSONDecodeError, OSError):
                continue
            if not isinstance(records, list):
                continue
            for rec in records:
                if not isinstance(rec, dict) or "request_key" not in rec:
                    continue
                self.cache_put(
                    source,
                    rec["request_key"],
                    rec.get("response"),
                    status_code=int(rec.get("status_code", 200) or 200),
                )
                loaded += 1
        return loaded

    def cache_all(self, source: str | None = None) -> list[dict[str, Any]]:
        """Return all api_cache rows (optionally for one source) as dicts with the
        parsed `response`. Used by scripts/seed_cache.py to export seed files."""
        if source is None:
            rows = self._conn.execute(
                "SELECT source, request_key, response, status_code FROM api_cache "
                "ORDER BY source, request_key"
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT source, request_key, response, status_code FROM api_cache "
                "WHERE source=? ORDER BY request_key",
                (source,),
            ).fetchall()
        out: list[dict[str, Any]] = []
        for r in rows:
            out.append({
                "source": r["source"],
                "request_key": r["request_key"],
                "response": json.loads(r["response"]),
                "status_code": r["status_code"],
            })
        return out

    # --- runs & reports ----------------------------------------------------
    def create_run(self, query: str, run_id: str | None = None) -> str:
        run_id = run_id or uuid.uuid4().hex
        with self._write_lock, self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO runs(run_id, query, status) VALUES(?,?,?)",
                (run_id, query, "started"),
            )
            conn.commit()
        return run_id

    def set_run_status(self, run_id: str, status: str) -> None:
        with self._write_lock, self._connect() as conn:
            conn.execute("UPDATE runs SET status=? WHERE run_id=?", (status, run_id))
            conn.commit()

    def set_run_error(self, run_id: str, message: str) -> None:
        with self._write_lock, self._connect() as conn:
            conn.execute(
                "UPDATE runs SET status='error', error=? WHERE run_id=?", (message, run_id)
            )
            conn.commit()

    def save_report(self, run_id: str, stage: str, payload: Any) -> None:
        """Persist a stage's contract. `payload` may be a Pydantic model or a dict."""
        body = payload.model_dump_json() if hasattr(payload, "model_dump_json") else json.dumps(payload)
        with self._write_lock, self._connect() as conn:
            conn.execute(
                """INSERT INTO reports(run_id, stage, payload) VALUES(?,?,?)
                   ON CONFLICT(run_id, stage) DO UPDATE SET
                     payload=excluded.payload, created_at=datetime('now')""",
                (run_id, stage, body),
            )
            conn.commit()

    def get_report(self, run_id: str, stage: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM reports WHERE run_id=? AND stage=?", (run_id, stage)
            ).fetchone()
        return json.loads(row["payload"]) if row else None

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
        return dict(row) if row else None

    # --- momentum model feature cache -------------------------------------
    def upsert_topic_features(
        self, openalex_id: str, name: str, features: dict, label: int | None,
        growth: float | None = None,
    ) -> None:
        with self._write_lock, self._connect() as conn:
            conn.execute(
                """INSERT INTO topic_features(openalex_id, name, features, label, growth, updated_at)
                   VALUES(?,?,?,?,?,?)
                   ON CONFLICT(openalex_id) DO UPDATE SET
                     name=excluded.name, features=excluded.features,
                     label=excluded.label, growth=excluded.growth, updated_at=excluded.updated_at""",
                (openalex_id, name, json.dumps(features), label, growth, _now()),
            )
            conn.commit()

    def all_topic_features(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM topic_features").fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["features"] = json.loads(d["features"])
            out.append(d)
        return out

    # --- calibration groups (real ChEMBL IC50 measurement groups) ---------
    def upsert_calibration_group(
        self, target_chembl_id: str, molecule_chembl_id: str,
        values_nM: list[float], activity_ids: list, document_ids: list | None = None,
    ) -> None:
        with self._write_lock, self._connect() as conn:
            conn.execute(
                """INSERT INTO calibration_groups(
                       target_chembl_id, molecule_chembl_id, values_nM, activity_ids,
                       document_ids, updated_at)
                   VALUES(?,?,?,?,?,?)
                   ON CONFLICT(target_chembl_id, molecule_chembl_id) DO UPDATE SET
                     values_nM=excluded.values_nM, activity_ids=excluded.activity_ids,
                     document_ids=excluded.document_ids, updated_at=excluded.updated_at""",
                (target_chembl_id, molecule_chembl_id, json.dumps(values_nM),
                 json.dumps(activity_ids), json.dumps(document_ids or []), _now()),
            )
            conn.commit()

    def all_calibration_groups(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM calibration_groups").fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["values_nM"] = json.loads(d["values_nM"])
            d["activity_ids"] = json.loads(d["activity_ids"])
            d["document_ids"] = json.loads(d.get("document_ids") or "[]")
            out.append(d)
        return out

    def close(self) -> None:
        """No-op: connections are per-operation and closed by their context managers."""
        return None


_singleton: Database | None = None


def get_db() -> Database:
    """Process-wide shared handle (fine for the hackathon's scale)."""
    global _singleton
    if _singleton is None:
        _singleton = Database()
    return _singleton


def init_db(path: str | Path | None = None, seed: bool = True) -> Database:
    """Create the DB, apply the schema, and (by default) load the offline cache seed.

    Seeding makes a fresh clone demo-ready in one command: the committed
    `database/seed/*.json` are poured into `api_cache` so the pipeline can run offline.
    Pass `seed=False` to skip it (e.g. throwaway test DBs). A missing/empty seed dir is
    a no-op. Returns the `Database` handle.
    """
    db = Database(path)
    if seed:
        db.load_seed()
    return db


def load_seed(db: Database | None = None, seed_dir: str | Path | None = None) -> int:
    """Load the committed offline cache seed into `db` (default: the shared handle).

    Convenience wrapper over `Database.load_seed`. Returns the number of rows loaded.
    """
    db = db or get_db()
    return db.load_seed(seed_dir)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
