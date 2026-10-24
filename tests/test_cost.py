"""B0.5: cost counted from the run log, not the formula."""

from __future__ import annotations

import pytest

from backend.contracts import ProtocolStep
from backend.stage2_design import design_experiment
from backend.stage3_protocol import compile_design, simulate_protocol
from backend.stage3_protocol.simulator import _HAVE_OPENTRONS, _cost_from_steps


def _steps(items):
    return [ProtocolStep(i=i, **kw) for i, kw in enumerate(items)]


def test_cost_counts_tips_compound_and_leaf_actions():
    steps = _steps([
        {"action": "pick_up_tip", "slot": "D1", "well": "A1"},
        {"action": "aspirate", "uL": 50.0, "slot": "D3", "well": "A2"},   # compound well
        {"action": "dispense", "uL": 50.0, "slot": "D2", "well": "A1"},
        {"action": "aspirate", "uL": 100.0, "slot": "D3", "well": "A1"},  # diluent, NOT counted
        {"action": "drop_tip", "slot": "A3"},
        {"action": "pick_up_tip", "slot": "D1", "well": "A2"},
        {"action": "transfer"},  # not a leaf action
    ])
    cost = _cost_from_steps(steps, "protocols/x.py")
    assert cost.tips == 2                     # two pick_up_tip
    assert cost.compound_uL == 50.0           # only the D3/A2 aspirate
    assert cost.plates == 1
    # leaf actions here: 2 pick_up_tip + 2 aspirate + 1 dispense + 1 drop_tip = 6 (transfer excluded)
    assert cost.robot_steps == 6
    assert cost.source.type.value == "simulator"


def test_leaf_action_count_excludes_transfer():
    # leaf actions: pick_up_tip, aspirate, dispense, drop_tip, blow_out, touch_tip, move_to
    steps = _steps([
        {"action": "pick_up_tip"}, {"action": "aspirate", "uL": 1.0},
        {"action": "dispense", "uL": 1.0}, {"action": "drop_tip"},
        {"action": "transfer"}, {"action": "mix"},  # transfer/mix are NOT leaf
    ])
    cost = _cost_from_steps(steps, "p.py")
    assert cost.robot_steps == 4


def test_offline_fallback_cost_is_assumed(tmp_path):
    if _HAVE_OPENTRONS:
        pytest.skip("opentrons installed; fallback not exercised")
    design = design_experiment(compound_chembl_id="CHEMBL554")
    sim = simulate_protocol(compile_design(design), design)
    assert sim.cost.source.type.value == "assumed"


@pytest.mark.skipif(not _HAVE_OPENTRONS, reason="opentrons not installed")
def test_live_cost_matches_run_log():
    design = design_experiment(compound_chembl_id="CHEMBL554")
    sim = simulate_protocol(compile_design(design), design)
    assert sim.cost.source.type.value == "simulator"
    # recompute expected straight from the parsed steps (robust to template changes in B1.1)
    exp_tips = sum(1 for s in sim.steps if s.action == "pick_up_tip")
    exp_compound = sum((s.uL or 0.0) for s in sim.steps
                       if s.action == "aspirate" and s.slot == "D3" and s.well == "A2")
    assert sim.cost.tips == exp_tips
    assert sim.cost.compound_uL == exp_compound
