"""B2.4: GET /api/evidence/{compound_chembl_id}."""

from __future__ import annotations

import pytest

fastapi_testclient = pytest.importorskip("fastapi.testclient")
from fastapi.testclient import TestClient  # noqa: E402

from backend.api import app  # noqa: E402
from backend.stage2_design import load_evidence  # noqa: E402

client = TestClient(app)


def test_evidence_for_known_compound():
    ev = load_evidence()
    if not ev:
        pytest.skip("evidence.json not built")
    compound = "CHEMBL554"  # lapatinib
    r = client.get(f"/api/evidence/{compound}")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) >= 1
    first = rows[0]
    for key in ("pmid", "title", "abstract", "year", "journal", "document_chembl_id"):
        assert key in first
    assert first["abstract"]


def test_unknown_compound_404():
    assert client.get("/api/evidence/CHEMBL000000").status_code == 404
