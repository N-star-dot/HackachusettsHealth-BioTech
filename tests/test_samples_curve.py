"""B1.3: samples and a curve band for the dashboard charts."""

from __future__ import annotations

from backend.stage2_design import design_experiment
from backend.stage4_uncertainty import run_uncertainty


def test_samples_present_and_consistent():
    d = design_experiment(compound_chembl_id="CHEMBL554")
    rep = run_uncertainty(d, runs=250, seed=42)
    s = rep.samples
    assert s is not None
    n = len(s["true_ic50_nM"])
    assert n == 250  # <= min(runs, 300)
    assert len(s["recovered_ic50_nM"]) == n and len(s["fold_error"]) == n
    for t, r, fe in zip(s["true_ic50_nM"], s["recovered_ic50_nM"], s["fold_error"]):
        assert abs(fe - max(r / t, t / r)) < 1e-6


def test_samples_capped_at_300():
    d = design_experiment(compound_chembl_id="CHEMBL554")
    rep = run_uncertainty(d, runs=500, seed=1)
    assert len(rep.samples["true_ic50_nM"]) == 300


def test_curve_band_shape():
    d = design_experiment(compound_chembl_id="CHEMBL554")
    rep = run_uncertainty(d, runs=200, seed=42)
    c = rep.curve
    assert c is not None
    p = d.dilution.points
    assert len(c["concentrations_nM"]) == p
    for key in ("activity_p10", "activity_p50", "activity_p90"):
        assert len(c[key]) == p
    # p10 <= p50 <= p90 at every concentration
    for lo, mid, hi in zip(c["activity_p10"], c["activity_p50"], c["activity_p90"]):
        assert lo <= mid <= hi
