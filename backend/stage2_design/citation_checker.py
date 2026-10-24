"""Deterministic citation checker. Owner B.

SECURITY MODEL (the hard rule): only text that CODE can prove is ever marked verified.
Nothing the LLM wrote in its own words gets a green badge — code cannot prove a
paraphrase preserves meaning, nor catch negation or unit swaps.

  * chembl_activity — we IGNORE the incoming claim text and re-render it from the record
    with one canonical template. Verified iff the activity id belongs to this pair. There
    is no free text left to forge.
  * abstract_quote — the verified thing is the QUOTE, not the model's note. A quote is
    verified only if (after normalising both sides) it equals a run of one-or-more WHOLE
    sentences of that pmid's abstract, is >= 8 words, and names the compound or target.
    The LLM's own sentence rides along as `model_note` and is NEVER verified.
"""

from __future__ import annotations

import re
import unicodedata

from backend.contracts import ExperimentDesign, RationaleItem

_MIN_QUOTE_WORDS = 8


def _normalise(text: str) -> str:
    """NFKC + collapsed whitespace + lowercase. Applied to BOTH sides at check time, so
    case and whitespace never matter."""
    text = unicodedata.normalize("NFKC", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text.lower()


def _split_sentences(abstract: str) -> list[str]:
    """Split an abstract into sentences on ., !, ? boundaries. Coarse but sufficient:
    we only need the set of whole-sentence spans to compare a quote against."""
    parts = re.split(r"(?<=[.!?])\s+", abstract.strip())
    return [p.strip() for p in parts if p.strip()]


def _sentence_runs(sentences: list[str]) -> set[str]:
    """All normalised runs of consecutive whole sentences (1..n). A verified quote must
    equal one of these — a partial-sentence snippet can't match."""
    runs: set[str] = set()
    norm = [_normalise(s) for s in sentences]
    for i in range(len(norm)):
        acc = norm[i]
        runs.add(acc)
        for j in range(i + 1, len(norm)):
            acc = acc + " " + norm[j]
            runs.add(acc)
    return runs


def _canonical_chembl_claim(value_nM: float, compound: str, target: str) -> str:
    """The ONE template for a ChEMBL activity claim. Code owns every character."""
    return (f"ChEMBL activity record: half-maximal inhibitory concentration "
            f"{value_nM:g} nM for compound {compound} against target {target}.")


def check_claim(
    item: RationaleItem,
    pair_activity_values: dict[str, float],
    evidence_abstracts: dict[str, str],
    compound_id: str = "",
    target_id: str = "",
    compound_names: tuple[str, ...] = (),
    target_names: tuple[str, ...] = (),
) -> RationaleItem:
    """Verify one rationale item. See module docstring for the security model."""

    if item.evidence_type == "chembl_activity":
        aid = str(item.evidence_id)
        if aid not in pair_activity_values:
            return item.model_copy(update={
                "status": "unverified",
                "reason": f"activity {aid} not in this pair's records",
            })
        # Re-render the claim from the record itself — discard whatever free text came in.
        value = pair_activity_values[aid]
        canonical = _canonical_chembl_claim(value, compound_id, target_id)
        return item.model_copy(update={
            "claim": canonical,
            "model_note": None,
            "status": "verified",
            "reason": None,
        })

    if item.evidence_type == "abstract_quote":
        pmid = str(item.evidence_id or item.pmid)
        # whatever the model wrote in `claim` is just a note, never verified
        model_note = item.model_note or item.claim or None

        if pmid not in evidence_abstracts:
            return item.model_copy(update={
                "model_note": model_note, "status": "unverified",
                "reason": f"pmid {pmid} not in this pair's evidence set",
            })
        if not item.quote:
            return item.model_copy(update={
                "model_note": model_note, "status": "unverified",
                "reason": "no quote provided",
            })

        norm_quote = _normalise(item.quote)
        if len(norm_quote.split()) < _MIN_QUOTE_WORDS:
            return item.model_copy(update={
                "model_note": model_note, "status": "unverified",
                "reason": f"quote has <{_MIN_QUOTE_WORDS} words",
            })

        runs = _sentence_runs(_split_sentences(evidence_abstracts[pmid]))
        if norm_quote not in runs:
            return item.model_copy(update={
                "model_note": model_note, "status": "unverified",
                "reason": "quote is not an exact run of whole sentences from the abstract",
            })

        names = tuple(_normalise(n) for n in (compound_names + target_names) if n)
        if names and not any(n in norm_quote for n in names):
            return item.model_copy(update={
                "model_note": model_note, "status": "unverified",
                "reason": "quote does not mention the compound or target",
            })

        # The QUOTE is a verbatim sentence from the paper. That is all a green badge means.
        return item.model_copy(update={
            "model_note": model_note, "status": "verified", "reason": None,
        })

    return item.model_copy(update={
        "status": "unverified", "reason": f"unknown evidence_type '{item.evidence_type}'",
    })


def check_citations(
    design: ExperimentDesign,
    pair: dict | None = None,
    evidence_abstracts: dict[str, str] | None = None,
    compound_names: tuple[str, ...] = (),
    target_names: tuple[str, ...] = (),
) -> ExperimentDesign:
    """Check every rationale item against this design's evidence."""
    pair_values: dict[str, float] = {}
    if pair:
        for p in pair.get("prior", {}).get("papers", []):
            pair_values[str(p["activity_id"])] = float(p["value_nM"])
    evidence_abstracts = evidence_abstracts or {}
    compound_id = design.assay.compound_chembl_id
    target_id = design.assay.target_chembl_id
    # the ChEMBL ids themselves always count as acceptable names-in-quote
    cnames = compound_names or (compound_id,)
    tnames = target_names or (target_id,)

    checked = [
        check_claim(item, pair_values, evidence_abstracts,
                    compound_id=compound_id, target_id=target_id,
                    compound_names=cnames, target_names=tnames)
        for item in design.rationale
    ]
    return design.model_copy(update={"rationale": checked})


def citation_error_rate(design: ExperimentDesign) -> float:
    """Share of rationale items not fully verified. Reported before/after checking."""
    if not design.rationale:
        return 0.0
    bad = sum(1 for r in design.rationale if r.status != "verified")
    return bad / len(design.rationale)
