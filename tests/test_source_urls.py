"""B1.6: Source.url filled where a canonical link exists."""

from __future__ import annotations

from backend.contracts.common import SourceType, source_url
from backend.stage2_design import design_experiment


def test_source_url_builder():
    assert source_url(SourceType.OPENALEX, "T10966") == "https://openalex.org/T10966"
    assert source_url(SourceType.CHEMBL_ACTIVITY, "190222,1766835") == \
        "https://www.ebi.ac.uk/chembl/explore/activities/190222"
    assert source_url(SourceType.PUBMED, "14684309") == "https://pubmed.ncbi.nlm.nih.gov/14684309/"
    assert source_url(SourceType.PAPER, "doi:10.1/x") == "https://doi.org/10.1/x"
    assert "opentrons.com" in source_url(SourceType.SPEC, "x")
    # no meaningful link for these
    assert source_url(SourceType.SIMULATOR, "p.py") is None
    assert source_url(SourceType.SIMULATED, "offline") is None
    assert source_url(SourceType.ASSUMED, "fixed-prior") is None


def test_designer_prior_and_rationale_have_urls():
    d = design_experiment(compound_chembl_id="CHEMBL554")
    # the prior links the compound report card (human-viewable)
    assert d.prior_ic50.source.url and "chembl" in d.prior_ic50.source.url
    assert "explore/compound" in d.prior_ic50.source.url
    for item in d.rationale:
        assert item.url and "chembl" in item.url
        assert "explore/document" in item.url  # citation links its source paper
        assert item.document_chembl_id  # looked up from the pair's papers
