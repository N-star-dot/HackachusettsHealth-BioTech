"""B1.1: compiler v2 — all replicates and controls pipetted, volumes tied to the factor.

The property test runs on the real simulator (labplanner / Python 3.12), so it's gated on
opentrons. The contract-validation and cost_model parts run everywhere.
"""

from __future__ import annotations

import math

import pytest

from backend.contracts import (
    Assay, Controls, Dilution, ExperimentDesign, Plate, PriorIC50, Source, Volumes,
)
from backend.contracts.common import SourceType
from backend.stage3_protocol import compile_design, cost_model, simulate_protocol
from backend.stage3_protocol.simulator import _HAVE_OPENTRONS


def _design(points=10, replicates=3, factor=3.0, transfer=50.0, pos=4, neg=4, did="d-test"):
    diluent = transfer * (factor - 1.0)
    return ExperimentDesign(
        design_id=did, topic_id="T",
        assay=Assay(target_chembl_id="CHEMBL1824", compound_chembl_id="CHEMBL554"),
        prior_ic50=PriorIC50(median_nM=24.0, n_measurements=21, spread_log10=0.93,
                             source=Source(type=SourceType.CHEMBL_ACTIVITY, id="x")),
        dilution=Dilution(top_nM=2400.0, factor=factor, points=points),
        replicates=replicates,
        controls=Controls(positive_wells=pos, negative_wells=neg),
        plate=Plate(layout="rows"),
        volumes_uL=Volumes(transfer=transfer, diluent=diluent),
    )


# --- contract validation (everywhere) ---
def test_volumes_must_match_factor():
    with pytest.raises(ValueError):
        ExperimentDesign(
            design_id="d", topic_id="T",
            assay=Assay(target_chembl_id="a", compound_chembl_id="b"),
            prior_ic50=PriorIC50(median_nM=10, n_measurements=1, spread_log10=0.5,
                                 source=Source(type=SourceType.CHEMBL_ACTIVITY, id="x")),
            dilution=Dilution(top_nM=100, factor=3, points=5),
            replicates=1, controls=Controls(positive_wells=1, negative_wells=1),
            plate=Plate(), volumes_uL=Volumes(transfer=50, diluent=50),  # (50+50)/50=2 != 3
        )


def test_transfer_times_factor_capped_at_300():
    with pytest.raises(ValueError):
        _design(factor=8.0, transfer=50.0)  # 50*8 = 400 > 300


def test_cost_model_shape():
    c = cost_model(_design(points=10, replicates=3, pos=4, neg=4))
    # tips = R*(P+2) + 1 (neg) + 1 (pos) = 3*12 + 2 = 38
    assert c["tips"] == 38
    # compound = R*(transfer+diluent) + pos*diluent = 3*150 + 4*100 = 850
    assert c["compound_uL"] == 850.0


# --- property test on the real simulator ---
@pytest.mark.skipif(not _HAVE_OPENTRONS, reason="opentrons not installed")
def test_compiler_v2_property():
    from hypothesis import given, settings
    from hypothesis import strategies as st

    @settings(max_examples=25, deadline=None)
    @given(
        points=st.integers(4, 11),
        replicates=st.integers(1, 8),
        factor=st.sampled_from([2.0, 2.5, 3.0, 4.0, 5.0]),
        transfer=st.integers(5, 60).map(float),
        pos=st.integers(0, 4),
        neg=st.integers(0, 4),
    )
    def _prop(points, replicates, factor, transfer, pos, neg):
        if transfer * factor > 300:
            return  # outside the valid regime; the contract would reject it
        # well budget: points*replicates + controls <= 96
        if points * replicates + pos + neg > 96:
            return
        d = _design(points=points, replicates=replicates, factor=factor,
                    transfer=transfer, pos=pos, neg=neg, did="d-prop")
        sim = simulate_protocol(compile_design(d), d)
        assert sim.simulator.passed, sim.simulator.error
        # cost_model matches the run-log count for tips and compound
        c = cost_model(d)
        assert sim.cost.tips == c["tips"]
        assert abs(sim.cost.compound_uL - c["compound_uL"]) < 1e-6

    _prop()
