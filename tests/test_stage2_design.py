"""Stage 2 tests: deterministic designer + the never-pass-a-false-claim checker.

The governing rule under test: the checker MAY flag a true claim, but must NEVER verify
a false one. The adversarial set below must all come back unverified or partial.
"""

from __future__ import annotations

import math

from backend.contracts import ExperimentDesign, RationaleItem
from backend.contracts.common import Source, SourceType
from backend.contracts.experiment_design import (
    Assay, Controls, Dilution, Plate, PriorIC50, Volumes,
)
from backend.stage2_design import check_citations, design_from_pair, load_demo_pairs
from backend.stage2_design.citation_checker import check_claim

# --- a synthetic pair + evidence set we fully control ---
_PAIR = {
    "target_chembl_id": "CHEMBL260",
    "compound_chembl_id": "CHEMBL10",
    "prior": {
        "median_nM": 64.0, "spread_log10": 0.8, "n_papers": 2,
        "activity_ids": [706787, 45892],
        "papers": [
            {"document_chembl_id": "DOCA", "activity_id": 706787, "value_nM": 50.0, "pchembl_value": 7.3},
            {"document_chembl_id": "DOCB", "activity_id": 45892, "value_nM": 80.0, "pchembl_value": 7.1},
        ],
    },
}
# normalised abstract text for one pmid in this pair's evidence set
_EVIDENCE = {"12345678": "sb-203580 inhibited p38 with an ic50 of 50 nm in this assay."}


def _mk(claim, evidence_type, evidence_id, quote=None):
    return RationaleItem(claim=claim, evidence_type=evidence_type,
                         evidence_id=str(evidence_id), quote=quote, pmid=str(evidence_id))


# ---------- deterministic designer ----------
def test_designer_builds_valid_design_for_every_demo_pair():
    pairs = load_demo_pairs()
    assert pairs, "demo_pairs.json missing — run scripts/build_demo_pairs.py"
    for pair in pairs:
        d = design_from_pair(pair)
        assert isinstance(d, ExperimentDesign)
        assert d.assay.compound_chembl_id == pair["compound_chembl_id"]
        # dilution covers the prior by >= 2 log units each side
        assert d.dilution.log10_span_each_side(d.prior_ic50.median_nM) >= 2.0 - 1e-6
        # well budget
        used = d.dilution.points * d.replicates + d.controls.positive_wells + d.controls.negative_wells
        assert used <= 96
        # every transfer >= 5 uL
        assert d.volumes_uL.transfer >= 5.0


def test_designer_dilution_caps_at_100000():
    pair = {
        "target_chembl_id": "T", "compound_chembl_id": "C",
        "prior": {"median_nM": 5000.0, "spread_log10": 2.0, "n_papers": 1, "activity_ids": [], "papers": []},
    }
    d = design_from_pair(pair)
    assert d.dilution.top_nM <= 100_000.0


# ---------- checker: true chembl_activity claim verifies ----------
def test_true_chembl_claim_verifies():
    item = _mk("IC50 of 50 nM was reported.", "chembl_activity", 706787)
    out = check_claim(item, {"706787": 50.0, "45892": 80.0}, {})
    assert out.status == "verified"


# ---------- adversarial set: all must be unverified or partial ----------
def test_adversarial_fake_pmid():
    item = _mk("claim", "abstract_quote", "99999999", quote="anything")
    out = check_claim(item, {}, _EVIDENCE)
    assert out.status != "verified"


def test_adversarial_real_pmid_outside_set():
    # a real PMID, but not in THIS pair's evidence set
    item = _mk("claim", "abstract_quote", "11111111", quote="sb-203580 inhibited p38")
    out = check_claim(item, {}, _EVIDENCE)
    assert out.status != "verified"


def test_adversarial_invented_quote():
    item = _mk("claim", "abstract_quote", "12345678", quote="this sentence is not in the abstract")
    out = check_claim(item, {}, _EVIDENCE)
    assert out.status != "verified"


def test_adversarial_real_quote_one_number_changed():
    # quote IS in the abstract, but the claim states a different number -> at most 'partial'
    item = _mk("the ic50 was 99 nM", "abstract_quote", "12345678",
               quote="ic50 of 50 nm")
    out = check_claim(item, {}, _EVIDENCE)
    assert out.status != "verified"  # 99 not in the quote -> partial, never verified


def test_chembl_claim_wrong_number_never_verifies():
    item = _mk("IC50 of 999 nM.", "chembl_activity", 706787)
    out = check_claim(item, {"706787": 50.0}, {})
    assert out.status == "unverified"


def test_chembl_claim_wrong_activity_id_never_verifies():
    item = _mk("IC50 of 50 nM.", "chembl_activity", 123)  # id not in pair
    out = check_claim(item, {"706787": 50.0}, {})
    assert out.status == "unverified"
