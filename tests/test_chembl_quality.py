"""Data-quality guards for the ChEMBL calibration pull.

These protect the calibration number's meaning:
  * censored / flagged / duplicate / cell-based / mutant records never survive,
  * each paper votes once (document-collapsed),
  * every calibration group spans >= 3 independent papers.
"""

from __future__ import annotations

from pipeline.ingest import chembl
from pipeline.ingest.chembl import _clean_activities, _collapse_by_document


def _raw(**kw):
    base = {
        "activity_id": 1,
        "molecule_chembl_id": "CHEMBL1",
        "document_chembl_id": "DOC1",
        "standard_value": "100.0",
        "standard_units": "nM",
        "pchembl_value": "7.0",
        "potential_duplicate": 0,
        "assay_type": "B",
        "assay_variant_mutation": None,
    }
    base.update(kw)
    return base


def test_censored_records_dropped():
    """A '>10000' record has no pChEMBL and must be rejected."""
    acts = [
        _raw(pchembl_value=None, standard_value="10000", standard_relation=">"),
        _raw(),
    ]
    cleaned = _clean_activities(acts)
    assert len(cleaned) == 1
    assert cleaned[0]["pchembl_value"] == 7.0


def test_flagged_and_duplicate_records_dropped():
    acts = [
        _raw(potential_duplicate=1),   # re-reported measurement
        _raw(pchembl_value=None),      # quality-flagged -> no pChEMBL
        _raw(activity_id=2),           # good
    ]
    cleaned = _clean_activities(acts)
    assert len(cleaned) == 1
    assert cleaned[0]["activity_id"] == 2


def test_cell_based_and_mutant_records_dropped():
    acts = [
        _raw(assay_type="F"),                         # functional / cell-based
        _raw(assay_variant_mutation="T790M"),         # mutant target
        _raw(activity_id=3),                          # good: B + wild-type
    ]
    cleaned = _clean_activities(acts)
    assert len(cleaned) == 1
    assert cleaned[0]["activity_id"] == 3


def test_document_collapse_one_value_per_paper():
    """A paper with many records collapses to one (its median pChEMBL)."""
    rows = _clean_activities([
        _raw(document_chembl_id="DOCA", pchembl_value="7.0"),
        _raw(document_chembl_id="DOCA", pchembl_value="8.0"),  # same paper
        _raw(document_chembl_id="DOCB", pchembl_value="6.0"),
    ])
    papers = _collapse_by_document(rows)
    assert len(papers) == 2  # DOCA collapsed to one, DOCB one
    doca = next(p for p in papers if p["document_chembl_id"] == "DOCA")
    assert doca["pchembl_value"] == 7.5  # median of 7.0 and 8.0


def test_pchembl_converts_to_nM():
    assert abs(chembl.pchembl_to_nM(9.0) - 1.0) < 1e-9    # pChEMBL 9 == 1 nM
    assert abs(chembl.pchembl_to_nM(6.0) - 1000.0) < 1e-6  # pChEMBL 6 == 1000 nM


def test_every_calibration_group_spans_three_papers():
    """Integration guard: DB groups must each span >= 3 papers. Skips if unpopulated."""
    from database import get_db

    groups = get_db().all_calibration_groups()
    if not groups:
        import pytest

        pytest.skip("calibration_groups not populated (run build_calibration_data.py)")
    for g in groups:
        assert len(g["values_nM"]) >= 3, f"group {g['molecule_chembl_id']} has <3 values"
        assert len(g.get("document_ids", [])) >= 3, (
            f"group {g['molecule_chembl_id']} spans <3 papers — not enough labs"
        )
