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


def _db_path() -> Path:
    return Path(os.environ.get("DATABASE_URL", str(_DEFAULT_DB)))


class Database:
    """Lightweight handle. Create once and share, or use `get_db()`."""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else _db_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA busy_timeout = 5000;")
        # B2.1: the connection is shared across the async worker thread and the request
        # thread, so serialise writes with a lock.
        self._write_lock = __import__("threading").Lock()
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self._conn.executescript(_SCHEMA_PATH.read_text())
        self._migrate()
        self._conn.commit()

    def _migrate(self) -> None:
        """Idempotent migrations for DBs created before a column was added."""
        cols = {r["name"] for r in self._conn.execute("PRAGMA table_info(topic_features)")}
        if "growth" not in cols:
            self._conn.execute("ALTER TABLE topic_features ADD COLUMN growth REAL")
        cal_cols = {r["name"] for r in self._conn.execute("PRAGMA table_info(calibration_groups)")}
        if cal_cols and "document_ids" not in cal_cols:
            self._conn.execute(
                "ALTER TABLE calibration_groups ADD COLUMN document_ids TEXT NOT NULL DEFAULT '[]'"
            )
        run_cols = {r["name"] for r in self._conn.execute("PRAGMA table_info(runs)")}
        if "error" not in run_cols:
            self._conn.execute("ALTER TABLE runs ADD COLUMN error TEXT")

    # --- api cache ---------------------------------------------------------
    def cache_get(self, source: str, request_key: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT response FROM api_cache WHERE source=? AND request_key=?",
            (source, request_key),
        ).fetchone()
        return json.loads(row["response"]) if row else None

    def cache_put(
        self, source: str, request_key: str, response: Any, status_code: int = 200
    ) -> None:
        self._conn.execute(
            """INSERT INTO api_cache(source, request_key, response, status_code, fetched_at)
               VALUES(?,?,?,?,?)
               ON CONFLICT(source, request_key) DO UPDATE SET
                 response=excluded.response,
                 status_code=excluded.status_code,
                 fetched_at=excluded.fetched_at""",
            (source, request_key, json.dumps(response), status_code, _now()),
        )
        self._conn.commit()

    # --- runs & reports ----------------------------------------------------
    def create_run(self, query: str, run_id: str | None = None) -> str:
        run_id = run_id or uuid.uuid4().hex
        with self._write_lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO runs(run_id, query, status) VALUES(?,?,?)",
                (run_id, query, "started"),
            )
            self._conn.commit()
        return run_id

    def set_run_status(self, run_id: str, status: str) -> None:
        with self._write_lock:
            self._conn.execute("UPDATE runs SET status=? WHERE run_id=?", (status, run_id))
            self._conn.commit()

    def set_run_error(self, run_id: str, message: str) -> None:
        with self._write_lock:
            self._conn.execute(
                "UPDATE runs SET status='error', error=? WHERE run_id=?", (message, run_id)
            )
            self._conn.commit()

    def save_report(self, run_id: str, stage: str, payload: Any) -> None:
        """Persist a stage's contract. `payload` may be a Pydantic model or a dict."""
        body = payload.model_dump_json() if hasattr(payload, "model_dump_json") else json.dumps(payload)
        with self._write_lock:
            self._conn.execute(
                """INSERT INTO reports(run_id, stage, payload) VALUES(?,?,?)
                   ON CONFLICT(run_id, stage) DO UPDATE SET
                     payload=excluded.payload, created_at=datetime('now')""",
                (run_id, stage, body),
            )
            self._conn.commit()

    def get_report(self, run_id: str, stage: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT payload FROM reports WHERE run_id=? AND stage=?", (run_id, stage)
        ).fetchone()
        return json.loads(row["payload"]) if row else None

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        row = self._conn.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
        return dict(row) if row else None

    # --- momentum model feature cache -------------------------------------
    def upsert_topic_features(
        self, openalex_id: str, name: str, features: dict, label: int | None,
        growth: float | None = None,
    ) -> None:
        self._conn.execute(
            """INSERT INTO topic_features(openalex_id, name, features, label, growth, updated_at)
               VALUES(?,?,?,?,?,?)
               ON CONFLICT(openalex_id) DO UPDATE SET
                 name=excluded.name, features=excluded.features,
                 label=excluded.label, growth=excluded.growth, updated_at=excluded.updated_at""",
            (openalex_id, name, json.dumps(features), label, growth, _now()),
        )
        self._conn.commit()

    def all_topic_features(self) -> list[dict[str, Any]]:
        rows = self._conn.execute("SELECT * FROM topic_features").fetchall()
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
        self._conn.execute(
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
        self._conn.commit()

    def all_calibration_groups(self) -> list[dict[str, Any]]:
        rows = self._conn.execute("SELECT * FROM calibration_groups").fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["values_nM"] = json.loads(d["values_nM"])
            d["activity_ids"] = json.loads(d["activity_ids"])
            d["document_ids"] = json.loads(d.get("document_ids") or "[]")
            out.append(d)
        return out

    def close(self) -> None:
        self._conn.close()


_singleton: Database | None = None


def get_db() -> Database:
    """Process-wide shared handle (fine for the hackathon's scale)."""
    global _singleton
    if _singleton is None:
        _singleton = Database()
    return _singleton


def init_db(path: str | Path | None = None) -> Database:
    """Create the DB and apply the schema. Used by scripts/setup."""
    return Database(path)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
