"""Smoke tests for the end-to-end pipeline and the safety gate."""

import pytest

from backend.safety import check_topic_safety
from backend.stage2_design import design_experiment
from backend.stage4_uncertainty import run_uncertainty
from pipeline import run_pipeline


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    """Keep the pipeline off the network: stage 1's OpenAlex lookups become cache
    misses that fall back to placeholder counts, so these tests stay deterministic."""
    monkeypatch.setenv("INGEST_OFFLINE", "1")


def test_safety_gate_blocks_dangerous_topic():
    gate = check_topic_safety("bioweapon synthesis protocol")
    assert gate.passed is False
    assert gate.reasons


def test_safety_gate_allows_benign_topic():
    gate = check_topic_safety("kinase inhibitors for liver fibrosis")
    assert gate.passed is True


def test_pipeline_runs_end_to_end():
    result = run_pipeline("kinase inhibitors for liver fibrosis", runs=100, persist=False)
    assert result.blocked is False
    assert result.topic.safety.passed
    assert result.sim is not None
    assert result.uncertainty is not None
    assert result.uncertainty.runs == 100
    # fold error is a ratio >= 1
    assert result.uncertainty.fold_error.p90 >= 1.0


def test_pipeline_stops_on_blocked_topic():
    result = run_pipeline("gain-of-function pathogen enhancement", runs=50, persist=False)
    assert result.blocked is True
    assert result.design is None


def test_uncertainty_is_deterministic_with_seed():
    d = design_experiment("T00000")
    a = run_uncertainty(d, runs=200, seed=1)
    b = run_uncertainty(d, runs=200, seed=1)
    assert a.fold_error.p90 == b.fold_error.p90
