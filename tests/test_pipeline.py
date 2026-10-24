"""Smoke tests for the end-to-end pipeline and the safety gate."""

from backend.safety import check_topic_safety
from backend.stage4_uncertainty import (
    calibrate,
    coverage_90,
    run_uncertainty,
    widen_until_calibrated,
)
from backend.stage2_design import design_experiment
from pipeline import run_pipeline


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


def test_calibration_coverage_on_synthetic_groups():
    """coverage_90 behaves: a spread matching the data gives ~0.9 coverage."""
    import numpy as np

    rng = np.random.default_rng(0)
    groups = [list(10 ** rng.normal(2.0, 0.68, size=5)) for _ in range(300)]
    cal = coverage_90(groups, spread_log10=0.68)
    assert 0.80 <= cal.coverage_90 <= 0.98
    assert cal.pairs == 300


def test_widen_raises_coverage():
    """Widening the assumed spread never lowers coverage."""
    import numpy as np

    rng = np.random.default_rng(1)
    # data is wider than the starting assumption -> starts under-covered
    groups = [list(10 ** rng.normal(2.0, 1.0, size=5)) for _ in range(300)]
    final_spread, before, after = widen_until_calibrated(groups, target=0.90, start=0.5)
    assert after.coverage_90 >= before.coverage_90
    assert final_spread >= 0.5


def test_calibrate_from_db_is_populated_or_zero():
    """calibrate() returns real coverage when groups exist, else a clean zero —
    never crashes. If the calibration table is populated, coverage must be in (0,1]."""
    cal = calibrate(0.68)
    assert 0.0 <= cal.coverage_90 <= 1.0
    if cal.pairs > 0:
        assert cal.coverage_90 > 0.0
