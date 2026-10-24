"""Integration tests for the frozen evidence set (data/demo/evidence.json).

Uses REAL abstracts. A genuine whole sentence from a real abstract verifies; an invented
sentence for the same PMID does not. Skips if the evidence set hasn't been built.
"""

from __future__ import annotations

import pytest

from backend.contracts import RationaleItem
from backend.stage2_design import evidence_abstracts_for, load_evidence
from backend.stage2_design.citation_checker import _split_sentences, check_claim


def _first_real_sentence(abstract: str, names: list[str]) -> str | None:
    """A whole sentence >=8 words that mentions one of `names` (so it passes the checker)."""
    for s in _split_sentences(abstract):
        low = s.lower()
        if len(s.split()) >= 8 and any(n in low for n in names):
            return s
    return None


def test_evidence_set_built_and_nonempty():
    ev = load_evidence()
    if not ev:
        pytest.skip("evidence.json not built — run scripts/build_evidence.py")
    # at least one pair with at least one abstract
    assert any(len(pmap) > 0 for pmap in ev.values())


def test_real_abstract_sentence_verifies_but_forgery_does_not():
    ev = load_evidence()
    if not ev:
        pytest.skip("evidence.json not built")

    # lapatinib / HER2 pair
    compound = "CHEMBL554"
    abstracts = evidence_abstracts_for(compound)
    if not abstracts:
        pytest.skip("no abstracts for CHEMBL554")

    names = ["egfr", "erbb2", "her2", "quinazoline", "inhibition"]
    pmid, sentence = None, None
    for pm, text in abstracts.items():
        s = _first_real_sentence(text, names)
        if s:
            pmid, sentence = pm, s
            break
    if not sentence:
        pytest.skip("no suitable real sentence found")

    kw = dict(compound_id=compound, target_id="CHEMBL1824",
              compound_names=(compound, "lapatinib"),
              target_names=("CHEMBL1824", "her2", "erbb2", "egfr", "quinazoline", "inhibition"))

    # real sentence -> verified
    good = RationaleItem(evidence_type="abstract_quote", evidence_id=pmid, pmid=pmid,
                         quote=sentence, claim="model paraphrase")
    out = check_claim(good, {}, abstracts, **kw)
    assert out.status == "verified"
    assert out.model_note == "model paraphrase"  # LLM text kept but not verified

    # invented sentence for the same real PMID -> never verified
    forged = RationaleItem(evidence_type="abstract_quote", evidence_id=pmid, pmid=pmid,
                           quote="This fabricated sentence is absolutely not in the abstract at all.",
                           claim="x")
    out2 = check_claim(forged, {}, abstracts, **kw)
    assert out2.status == "unverified"
