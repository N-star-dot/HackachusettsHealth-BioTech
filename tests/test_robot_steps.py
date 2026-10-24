"""B0.4: structured robot steps for the replay.

The live-simulator assertions require the opentrons package (Python <=3.13), so they are
skipped when it isn't installed. The parser itself is unit-tested against a synthetic run
log whose payloads mirror the real Opentrons 10.1.0 output, so it is covered everywhere.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.stage2_design import design_experiment
from backend.stage3_protocol import compile_design, simulate_protocol
from backend.stage3_protocol.simulator import _HAVE_OPENTRONS, _extract_steps, _deck_slots

# A synthetic run log shaped like the real one (flat list of {level, payload}).
_RUN_LOG = [
    {"level": 1, "payload": {
        "text": "Picking up tip from A1 of Opentrons Flex 96 Tip Rack 200 µL on slot D1"}},
    {"level": 1, "payload": {
        "text": "Aspirating 50.0 uL from A2 of NEST 12 Well Reservoir 15 mL on slot D3 at 716.0 uL/sec",
        "volume": 50.0,
        "location": "A2 of NEST 12 Well Reservoir 15 mL on slot D3"}},
    {"level": 1, "payload": {
        "text": "Dispensing 50.0 uL into A1 of Corning 96 Well Plate 360 µL Flat on slot D2",
        "volume": 50.0,
        "location": "A1 of Corning 96 Well Plate 360 µL Flat on slot D2"}},
    {"level": 2, "payload": {
        "text": "Mixing 3 times with a volume of 50.0 ul",
        "repetitions": 3, "volume": 50.0,
        "location": "A1 of Corning 96 Well Plate 360 µL Flat on slot D2"}},
    {"level": 1, "payload": {"text": "Dropping tip into Trash Bin on slot A3",
                             "location": "Trash Bin on slot A3"}},
]


def test_parser_structures_every_field():
    steps = _extract_steps(_RUN_LOG)
    assert len(steps) == len(_RUN_LOG)

    assert steps[0].action == "pick_up_tip"
    assert steps[0].slot == "D1" and steps[0].well == "A1"

    asp = steps[1]
    assert asp.action == "aspirate" and asp.uL == 50.0
    assert asp.slot == "D3" and asp.well == "A2"
    assert asp.source is not None and asp.source.well == "A2"

    disp = steps[2]
    assert disp.action == "dispense" and disp.uL == 50.0
    assert disp.slot == "D2" and disp.well == "A1"
    assert disp.dest is not None and disp.dest.well == "A1"

    mix = steps[3]
    assert mix.action == "mix" and mix.repetitions == 3

    drop = steps[4]
    assert drop.action == "drop_tip" and drop.slot == "A3"


def test_text_kept_verbatim():
    steps = _extract_steps(_RUN_LOG)
    assert steps[1].text.startswith("Aspirating 50.0 uL")


def test_deck_slots_from_constant():
    deck = _deck_slots()
    by_slot = {d.slot: d for d in deck}
    assert by_slot["D1"].role == "tips"
    assert by_slot["D2"].role == "plate"
    assert by_slot["D3"].role == "reservoir"
    assert by_slot["D3"].contents == {"A1": "diluent", "A2": "compound"}
    assert by_slot["A3"].role == "trash"


def test_static_fallback_returns_no_steps(tmp_path):
    """Without opentrons, steps must be empty (no fabricated replay), deck still present."""
    if _HAVE_OPENTRONS:
        pytest.skip("opentrons installed; fallback path not exercised")
    design = design_experiment(compound_chembl_id="CHEMBL554")
    path = compile_design(design)
    sim = simulate_protocol(path, design)
    assert sim.steps == []
    assert len(sim.deck) == 4
    assert "not installed" in sim.simulator.opentrons_version


@pytest.mark.skipif(not _HAVE_OPENTRONS, reason="opentrons not installed")
def test_live_simulator_steps_match_run_log():
    design = design_experiment(compound_chembl_id="CHEMBL554")
    path = compile_design(design)
    sim = simulate_protocol(path, design)
    assert sim.simulator.passed
    assert len(sim.steps) == sim.simulator.log_lines
    assert sim.steps[0].action == "pick_up_tip"
    assert sim.steps[0].slot == "D1"
    for s in sim.steps:
        if s.action in ("aspirate", "dispense"):
            assert s.uL is not None and s.slot and s.well
    pickups = sum(1 for s in sim.steps if s.action == "pick_up_tip")
    text_pickups = sum(1 for s in sim.steps if s.text.startswith("Picking up tip"))
    assert pickups == text_pickups
