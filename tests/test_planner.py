"""B1.2: planner uses the baseline's runs/seed/reader_cv and valid candidates only."""

from __future__ import annotations

from backend.stage2_design import design_experiment
from backend.stage4_uncertainty import plan_next_experiments, run_uncertainty


def _baseline(reader_cv=0.05):
    d = design_experiment(compound_chembl_id="CHEMBL554")
    return d, run_uncertainty(d, runs=200, seed=42, reader_cv=reader_cv)


def test_rankings_are_deterministic():
    d, base = _baseline()
    a = plan_next_experiments(d, base)
    b = plan_next_experiments(d, base)
    assert [x.change for x in a] == [x.change for x in b]
    assert [x.score for x in a] == [x.score for x in b]


def test_candidates_carry_design_and_p90_after():
    d, base = _baseline()
    plan = plan_next_experiments(d, base)
    assert plan, "expected at least one candidate"
    for ne in plan:
        assert ne.design is not None
        assert ne.p90_after is not None


def test_candidates_respect_plate_limits():
    # a 10-point design: 'add 2 dilution points' -> 12 points, which must be rejected
    d, base = _baseline()
    assert d.dilution.points == 10
    plan = plan_next_experiments(d, base, top_k=10)
    assert all("dilution points" not in ne.change for ne in plan)


def test_extra_cost_nonnegative():
    d, base = _baseline()
    for ne in plan_next_experiments(d, base):
        assert ne.extra_tips >= 0 and ne.extra_compound_uL >= 0 and ne.extra_plates >= 0
