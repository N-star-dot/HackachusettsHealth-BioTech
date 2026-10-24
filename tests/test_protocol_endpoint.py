"""B1.4: GET /api/protocol/{name}."""

from __future__ import annotations

import pytest

fastapi_testclient = pytest.importorskip("fastapi.testclient")
from fastapi.testclient import TestClient  # noqa: E402

from backend.api import app  # noqa: E402
from backend.stage2_design import design_experiment  # noqa: E402
from backend.stage3_protocol import compile_design  # noqa: E402

client = TestClient(app)


def test_get_existing_protocol():
    d = design_experiment(compound_chembl_id="CHEMBL554")
    compile_design(d)  # writes protocols/d-001.py
    r = client.get("/api/protocol/d-001")
    assert r.status_code == 200
    assert "def run(protocol)" in r.text
    assert r.headers["content-type"].startswith("text/plain")


def test_missing_protocol_404():
    assert client.get("/api/protocol/nope-not-here").status_code == 404


def test_bad_name_422():
    assert client.get("/api/protocol/..%2Fetc").status_code in (404, 422)
