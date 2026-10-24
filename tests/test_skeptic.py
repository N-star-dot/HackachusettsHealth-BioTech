"""B2.5: the Skeptic turn — LLM debate settled by simulation.

The live LLM path needs GEMINI_API_KEY; without it review_design returns []. The
clamping and verdict logic (the safety-critical parts) are unit-tested directly.
"""

from __future__ import annotations

import os

from backend.stage2_design import design_experiment, review_design
from backend.stage2_design.skeptic import _apply_and_clamp


def _design():
    return design_experiment(compound_chembl_id="CHEMBL554")


def test_no_key_means_empty_review(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    turns = review_design(_design(), baseline_p90=1.3, runs=50, seed=42, reader_cv=0.05)
    assert turns == []


def test_clamp_keeps_within_limits():
    d = _design()
    # propose an absurd top concentration -> clamped to <= 100000, still valid
    c = _apply_and_clamp(d, "dilution.top_nM", 10_000_000)
    assert c is not None and c.dilution.top_nM <= 100_000.0


def test_clamp_rejects_impossible_factor_volume():
    d = _design()
    # factor 10 with the 50 µL transfer -> 500 µL > 300 cap -> rejected
    d2 = d.model_copy()
    c = _apply_and_clamp(d2, "dilution.factor", 10.0)
    # clamp sets factor=10 then recomputes diluent; transfer*factor = 500 > 300 -> None
    assert c is None


def test_clamp_keeps_diluent_consistent():
    d = _design()
    c = _apply_and_clamp(d, "dilution.factor", 4.0)  # 50*4=200 <= 300, ok
    assert c is not None
    t, dl, f = c.volumes_uL.transfer, c.volumes_uL.diluent, c.dilution.factor
    assert abs((t + dl) / t - f) < 1e-6


def test_clamp_replicates_bounds():
    d = _design()
    c = _apply_and_clamp(d, "replicates", 99)
    # 11 points * 8 replicates + 8 controls = 96 -> ok at 8; but this design has 10 points,
    # 10*8+8 = 88 <= 96, so replicates clamps to 8 and stays valid
    assert c is not None and c.replicates == 8
