"""B1.5: the four fixed axes are computed from the design + sim, each sourced."""

from __future__ import annotations

from backend.stage1_topic import recompute_axes, score_topic
from backend.stage2_design import design_experiment
from backend.stage3_protocol import compile_design, simulate_protocol


def _report_design_sim():
    topic = score_topic("HER2 kinase inhibitors")
    design = design_experiment(compound_chembl_id="CHEMBL554")
    sim = simulate_protocol(compile_design(design), design)
    return recompute_axes(topic, design, sim), design, sim


def test_evidence_from_paper_count():
    report, design, sim = _report_design_sim()
    expected = min(1.0, design.prior_ic50.n_measurements / 20.0)
    assert abs(report.matrix.evidence - round(expected, 4)) < 1e-9
    assert report.matrix.axis_sources["evidence"].type.value == "chembl_activity"


def test_automatable_tracks_simulator_pass():
    report, design, sim = _report_design_sim()
    assert report.matrix.automatable == (1.0 if sim.simulator.passed else 0.0)
    assert report.matrix.axis_sources["automatable"].type.value == "simulator"


def test_cost_time_from_tips():
    report, design, sim = _report_design_sim()
    expected = round(1.0 - min(1.0, sim.cost.tips / 96.0), 4)
    assert report.matrix.cost_time == expected
    assert report.matrix.axis_sources["cost_time"].type.value == "simulator"


def test_total_recomputed_and_consistent():
    report, _, _ = _report_design_sim()
    m = report.matrix
    from backend.contracts import ViabilityMatrix
    axes = {"momentum": m.momentum, "novelty": m.novelty, "evidence": m.evidence,
            "automatable": m.automatable, "cost_time": m.cost_time}
    assert abs(m.total - ViabilityMatrix.weighted_total(axes, m.weights)) < 1e-6


def test_novelty_is_openalex_or_assumed():
    report, _, _ = _report_design_sim()
    assert report.matrix.axis_sources["novelty"].type.value in ("openalex", "assumed")
