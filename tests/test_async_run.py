"""B2.1: async run with live stage progress."""

from __future__ import annotations

import time

import pytest

fastapi_testclient = pytest.importorskip("fastapi.testclient")
from fastapi.testclient import TestClient  # noqa: E402

from backend.api import app  # noqa: E402

client = TestClient(app)


def test_async_returns_started_then_completes():
    posted = client.post("/api/run",
                         json={"query": "HER2 kinase inhibitors", "runs": 50, "mode": "async"}).json()
    assert posted["status"] == "started"
    run_id = posted["run_id"]

    # poll until done or error
    final = None
    for _ in range(120):  # up to ~12s
        got = client.get(f"/api/run/{run_id}").json()
        status = got["meta"]["status"]
        if status in ("done", "error"):
            final = got
            break
        time.sleep(0.1)

    assert final is not None, "async run did not finish in time"
    assert final["meta"]["status"] == "done"
    assert final["topic"] is not None
    assert final["uncertainty"] is not None


def test_sync_still_default():
    body = client.post("/api/run", json={"query": "HER2", "runs": 50}).json()
    assert body["status"] == "done"
    assert body["topic"] is not None
