"""B0.3: pick the compound-target pair from the question."""

from __future__ import annotations

import pytest

from backend.stage2_design.demo_pairs import match_pair

fastapi_testclient = pytest.importorskip("fastapi.testclient")
from fastapi.testclient import TestClient  # noqa: E402

from backend.api import app  # noqa: E402

client = TestClient(app)


def test_query_keyword_match():
    pair, match = match_pair("JAK inhibitors in autoimmune disease")
    assert pair["compound_chembl_id"] == "CHEMBL221959"
    assert match == "query"


def test_default_when_no_keyword():
    pair, match = match_pair("protein folding")
    assert match == "default"
    assert pair["compound_chembl_id"] == "CHEMBL554"  # first pair


def test_user_override_wins():
    pair, match = match_pair("anything at all", compound_chembl_id="CHEMBL10")
    assert pair["compound_chembl_id"] == "CHEMBL10"
    assert match == "user"


def test_her2_and_p38_keywords():
    assert match_pair("HER2 breast cancer")[0]["compound_chembl_id"] == "CHEMBL554"
    assert match_pair("p38 MAPK inflammation")[0]["compound_chembl_id"] == "CHEMBL10"


def test_run_uses_matched_pair():
    body = client.post("/api/run", json={"query": "JAK inhibitors", "runs": 50}).json()
    assert body["pair"]["compound_chembl_id"] == "CHEMBL221959"
    assert body["pair"]["match"] == "query"
    assert body["design"]["assay"]["compound_chembl_id"] == "CHEMBL221959"


def test_pairs_endpoint():
    out = client.get("/api/pairs").json()
    assert len(out) == 3
    assert {p["compound_chembl_id"] for p in out} == {"CHEMBL554", "CHEMBL10", "CHEMBL221959"}
    assert out[0]["prior"]["median_nM"] is not None
