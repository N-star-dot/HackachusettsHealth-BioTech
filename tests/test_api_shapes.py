"""B0.1: typed responses, one JSON shape per run.

POST /api/run and GET /api/run/{id} must return identical key structure (alias fields
like safety.pass, simulator.pass), and /openapi.json must expose RunResponse.
"""

from __future__ import annotations

import pytest

fastapi_testclient = pytest.importorskip("fastapi.testclient")
from fastapi.testclient import TestClient  # noqa: E402

from backend.api import app  # noqa: E402

client = TestClient(app)


def _keys_at_every_level(obj, path=""):
    """Flatten a nested dict/list into a set of dotted key paths (list index elided)."""
    out = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}" if path else k
            out.add(p)
            out |= _keys_at_every_level(v, p)
    elif isinstance(obj, list) and obj:
        out |= _keys_at_every_level(obj[0], path + "[]")
    return out


def test_openapi_has_run_response_schema():
    spec = client.get("/openapi.json").json()
    assert "RunResponse" in spec["components"]["schemas"]


def test_post_and_get_run_have_same_shape():
    posted = client.post("/api/run", json={"query": "HER2 kinase inhibitors", "runs": 50}).json()
    run_id = posted["run_id"]
    got = client.get(f"/api/run/{run_id}").json()

    # alias fields present in both
    assert "pass" in posted["topic"]["safety"]
    assert "pass" in got["topic"]["safety"]
    if posted["sim"]:
        assert "pass" in posted["sim"]["simulator"]
        assert "pass" in got["sim"]["simulator"]

    # same keys at every level, ignoring the extra top-level meta on the record
    pk = _keys_at_every_level(posted)
    gk = _keys_at_every_level(got) - {k for k in _keys_at_every_level(got) if k.startswith("meta")}
    assert pk <= gk, f"POST keys missing from GET: {pk - gk}"


def test_missing_run_is_404():
    assert client.get("/api/run/does-not-exist").status_code == 404
