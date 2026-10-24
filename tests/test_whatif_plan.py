"""B0.9: fast what-if — plan=false skips the planner's extra reruns."""

from __future__ import annotations

import pytest

fastapi_testclient = pytest.importorskip("fastapi.testclient")
from fastapi.testclient import TestClient  # noqa: E402

from backend.api import app  # noqa: E402
from backend.stage2_design import design_experiment  # noqa: E402

client = TestClient(app)


def _design_json():
    return design_experiment(compound_chembl_id="CHEMBL554").model_dump()


def test_plan_false_returns_no_next_experiments():
    body = client.post("/api/uncertainty",
                       json={"design": _design_json(), "runs": 100, "plan": False}).json()
    assert body["next_experiments"] == []


def test_plan_true_returns_next_experiments():
    body = client.post("/api/uncertainty",
                       json={"design": _design_json(), "runs": 100, "plan": True}).json()
    assert len(body["next_experiments"]) >= 1


def test_plan_defaults_true():
    body = client.post("/api/uncertainty",
                       json={"design": _design_json(), "runs": 100}).json()
    assert len(body["next_experiments"]) >= 1
