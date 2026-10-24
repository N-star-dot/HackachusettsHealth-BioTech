"""B0.8: one source per noise number."""

from __future__ import annotations

from backend.stage2_design import design_experiment
from backend.stage4_uncertainty import run_uncertainty


def test_lab_spread_credits_chembl_for_lapatinib():
    d = design_experiment(compound_chembl_id="CHEMBL554")  # prior spread 0.932 from ChEMBL
    rep = run_uncertainty(d, runs=50, seed=42)
    fs = rep.noise.field_sources
    assert fs["lab_spread_log10"].type.value == "chembl_activity"
    assert fs["pipette_cv"].type.value == "spec"
    assert fs["pipette_bias"].type.value == "spec"
    assert fs["reader_cv"].type.value == "assumed"


def test_pipette_source_links_opentrons_spec():
    d = design_experiment(compound_chembl_id="CHEMBL554")
    rep = run_uncertainty(d, runs=50, seed=42)
    assert "opentrons.com" in (rep.noise.field_sources["pipette_cv"].url or "")
