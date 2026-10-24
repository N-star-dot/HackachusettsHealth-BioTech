"""B2.3: GET /api/metrics."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

fastapi_testclient = pytest.importorskip("fastapi.testclient")
from fastapi.testclient import TestClient  # noqa: E402

from backend.api import app  # noqa: E402

client = TestClient(app)
_METRICS = Path(__file__).resolve().parents[1] / "models" / "metrics.json"


def test_metrics_endpoint_serves_file_or_404():
    r = client.get("/api/metrics")
    if _METRICS.is_file():
        assert r.status_code == 200
        body = r.json()
        # at least one known metric block with a description
        assert any("description" in v for v in body.values() if isinstance(v, dict))
    else:
        assert r.status_code == 404


def test_metrics_file_shape_if_present():
    if not _METRICS.is_file():
        pytest.skip("metrics.json not built")
    body = json.loads(_METRICS.read_text())
    if "momentum" in body:
        assert "auroc" in body["momentum"] and "description" in body["momentum"]
