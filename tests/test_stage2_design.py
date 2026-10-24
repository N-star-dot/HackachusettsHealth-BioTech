"""Stage 2 tests: deterministic designer + the never-pass-a-false-claim checker.

HARD RULE under test: only text code can prove is ever 'verified'. For chembl_activity
the claim is re-rendered from the record (no free text survives); for abstract_quote the
verified thing is a verbatim run of whole abstract sentences, >=8 words, naming the
compound/target. The LLM's own words ride along as `model_note` and are never verified.
"""

from __future__ import annotations

from backend.contracts import ExperimentDesign, RationaleItem
from backend.stage2_design import check_citations, design_from_pair, load_demo_pairs
from backend.stage2_design.citation_checker import (
    _canonical_chembl_claim,
    _normalise,
    _split_sentences,
    check_claim,
)

# abstract with a real affirmative sentence (original case, to catch the lowercase bug)
_ABSTRACT_RAW = ("Lapatinib inhibited HER2 with an IC50 of 9.2 nM in a biochemical kinase "
                 "assay. The compound was selective over related kinases.")
_PMID = "12345678"
_EVIDENCE = {_PMID: _ABSTRACT_RAW}  # stored with ORIGINAL CASE on purpose
_PAIR_VALUES = {"706787": 50.0}
_CNAMES = ("CHEMBL554", "lapatinib")
_TNAMES = ("CHEMBL1824", "HER2")


def _q(evidence_type, evidence_id, quote=None, claim="", note=None):
    return RationaleItem(claim=claim, evidence_type=evidence_type, evidence_id=str(evidence_id),
                         quote=quote, model_note=note, pmid=str(evidence_id))


def _check(item):
    return check_claim(item, _PAIR_VALUES, {k: v for k, v in _EVIDENCE.items()},
                       compound_id="CHEMBL554", target_id="CHEMBL1824",
                       compound_names=_CNAMES, target_names=_TNAMES)


# ---------------- deterministic designer ----------------
def test_designer_builds_valid_design_for_every_demo_pair():
    pairs = load_demo_pairs()
    assert pairs, "demo_pairs.json missing — run scripts/build_demo_pairs.py"
    for pair in pairs:
        d = design_from_pair(pair)
        assert isinstance(d, ExperimentDesign)
        assert d.assay.compound_chembl_id == pair["compound_chembl_id"]
        assert d.dilution.log10_span_each_side(d.prior_ic50.median_nM) >= 2.0 - 1e-6
        used = d.dilution.points * d.replicates + d.controls.positive_wells + d.controls.negative_wells
        assert used <= 96
        assert d.volumes_uL.transfer >= 5.0


def test_designer_cap_goes_to_notes_field():
    pair = {
        "target_chembl_id": "T", "compound_chembl_id": "C",
        "prior": {"median_nM": 5000.0, "spread_log10": 2.0, "n_papers": 1,
                  "activity_ids": [], "papers": []},
    }
    d = design_from_pair(pair)
    assert d.dilution.top_nM <= 100_000.0
    assert any("capped" in n for n in d.notes)


# ---------------- chembl_activity: claim re-rendered, forgeries defeated ----------------
def test_chembl_claim_rerendered_from_record():
    """Whatever free text comes in, the verified claim is the canonical render."""
    item = _q("chembl_activity", 706787, claim="totally made up nonsense")
    out = _check(item)
    assert out.status == "verified"
    assert out.claim == _canonical_chembl_claim(50.0, "CHEMBL554", "CHEMBL1824")
    assert "nonsense" not in out.claim  # incoming free text discarded


def test_chembl_forgery_wrong_unit_uM():
    out = _check(_q("chembl_activity", 706787, claim="IC50 of 50 uM"))
    # claim is re-rendered to nM; the forged µM text cannot survive
    assert "uM" not in out.claim and "nM" in out.claim


def test_chembl_forgery_no_number_inactive():
    out = _check(_q("chembl_activity", 706787, claim="the compound was inactive"))
    assert "inactive" not in out.claim


def test_chembl_forgery_wrong_compound():
    out = _check(_q("chembl_activity", 706787, claim="Aspirin shows IC50 of 50 nM"))
    assert "spirin" not in out.claim  # names come from the record, not the forged text


def test_chembl_unknown_activity_never_verifies():
    out = _check(_q("chembl_activity", 999, claim=""))
    assert out.status == "unverified"


# ---------------- abstract_quote: forgeries defeated ----------------
def test_quote_negation_claim_is_only_a_note():
    """A real quote stays verified, but a negating 'claim' is just model_note, never verified."""
    real_sentence = "Lapatinib inhibited HER2 with an IC50 of 9.2 nM in a biochemical kinase assay."
    out = _check(_q("abstract_quote", _PMID, quote=real_sentence,
                    claim="Lapatinib does NOT inhibit HER2."))
    assert out.status == "verified"
    assert out.model_note == "Lapatinib does NOT inhibit HER2."  # kept, but not verified
    # the verified artifact is the quote, which genuinely is in the abstract
    assert _normalise(out.quote) in _normalise(_ABSTRACT_RAW)


def test_quote_unit_mismatch_claim_is_only_a_note():
    real_sentence = "Lapatinib inhibited HER2 with an IC50 of 9.2 nM in a biochemical kinase assay."
    out = _check(_q("abstract_quote", _PMID, quote=real_sentence, claim="IC50 is 9.2 uM"))
    # quote verifies (it's real); the µM claim is only a note and never gets the badge
    assert out.status == "verified"
    assert "uM" in (out.model_note or "")


def test_one_word_quote_rejected():
    out = _check(_q("abstract_quote", _PMID, quote="lapatinib"))
    assert out.status == "unverified"  # < 8 words


def test_partial_sentence_quote_rejected():
    out = _check(_q("abstract_quote", _PMID, quote="inhibited HER2 with an IC50 of 9.2 nM in a"))
    assert out.status == "unverified"  # not a whole-sentence run


def test_fake_pmid_rejected():
    out = _check(_q("abstract_quote", "99999999",
                    quote="Lapatinib inhibited HER2 with an IC50 of 9.2 nM in a biochemical kinase assay."))
    assert out.status == "unverified"


def test_real_pmid_outside_set_rejected():
    out = _check(_q("abstract_quote", "11111111",
                    quote="Lapatinib inhibited HER2 with an IC50 of 9.2 nM in a biochemical kinase assay."))
    assert out.status == "unverified"


def test_quote_without_compound_or_target_rejected():
    # a real sentence from the abstract that names neither the compound nor the target
    out = _check(_q("abstract_quote", _PMID, quote="The compound was selective over related kinases."))
    assert out.status == "unverified"


def test_case_insensitive_quote_verifies():
    """Honest quote in a different case still verifies (both sides normalised)."""
    upper = "LAPATINIB INHIBITED HER2 WITH AN IC50 OF 9.2 NM IN A BIOCHEMICAL KINASE ASSAY."
    out = _check(_q("abstract_quote", _PMID, quote=upper))
    assert out.status == "verified"


# ---------------- the global invariant ----------------
def test_no_verified_text_is_unsupported():
    """Every verified item's attested text is either the canonical ChEMBL render or an
    exact abstract sentence-run. Nothing else can be green."""
    abstract_runs = {_normalise(s) for s in _split_sentences(_ABSTRACT_RAW)}
    # build a mix of honest + forged items
    items = [
        _q("chembl_activity", 706787, claim="forged"),
        _q("abstract_quote", _PMID,
           quote="Lapatinib inhibited HER2 with an IC50 of 9.2 nM in a biochemical kinase assay.",
           claim="model paraphrase"),
        _q("abstract_quote", _PMID, quote="lapatinib"),            # forgery
        _q("abstract_quote", "99999999", quote="x " * 10),         # forgery
    ]
    for item in items:
        out = _check(item)
        if out.status == "verified":
            if out.evidence_type == "chembl_activity":
                assert out.claim == _canonical_chembl_claim(50.0, "CHEMBL554", "CHEMBL1824")
            else:
                assert _normalise(out.quote) in abstract_runs
