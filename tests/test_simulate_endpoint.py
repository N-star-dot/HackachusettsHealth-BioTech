"""B0.6: POST /api/simulate for what-if designs."""

from __future__ import annotations

import pytest

fastapi_testclient = pytest.importorskip("fastapi.testclient")
from fastapi.testclient import TestClient  # noqa: E402

from backend.api import app  # noqa: E402
from backend.stage2_design import design_experiment  # noqa: E402
from backend.stage3_protocol.simulator import _HAVE_OPENTRONS  # noqa: E402

client = TestClient(app)


def test_bad_design_id_is_422():
    design = design_experiment(compound_chembl_id="CHEMBL554").model_dump()
    design["design_id"] = "../etc/passwd"  # not filename-safe
    r = client.post("/api/simulate", json={"design": design})
    assert r.status_code == 422


def test_simulate_returns_sim_result():
    design = design_experiment(compound_chembl_id="CHEMBL554").model_dump()
    design["design_id"] = "d-001-w3fa21c"  # dashboard-style what-if id
    r = client.post("/api/simulate", json={"design": design})
    assert r.status_code == 200
    body = r.json()
    assert body["design_id"] == "d-001-w3fa21c"
    assert "pass" in body["simulator"]
    # whatif protocol path, never the run's protocols/<design_id>.py
    assert "/whatif/" in body["protocol_file"]


@pytest.mark.skipif(not _HAVE_OPENTRONS, reason="opentrons not installed")
def test_simulate_matches_a_run():
    """The what-if sim of a design has the same step count as simulating it directly."""
    from backend.stage3_protocol import compile_design, simulate_protocol

    d = design_experiment(compound_chembl_id="CHEMBL554")
    direct = simulate_protocol(compile_design(d), d)

    payload = d.model_dump()
    payload["design_id"] = "d-001-wabc123"
    body = client.post("/api/simulate", json={"design": payload}).json()
    assert body["simulator"]["pass"] is True
    assert len(body["steps"]) == len(direct.steps)
