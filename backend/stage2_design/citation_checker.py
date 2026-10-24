"""Deterministic citation checker. Owner B.

Governing rule: the checker MAY wrongly flag a true claim, but it must NEVER pass a
false one. So every branch is conservative — anything that doesn't fully prove out is
'partial' or 'unverified', never 'verified'.

Two evidence types:
  * chembl_activity — verified only if the activity id belongs to THIS pair and every
    number in the claim equals that record's value.
  * abstract_quote  — verified only if the pmid is in this pair's evidence set, AND the
    lowercased normalised quote is a substring of that pmid's stored abstract, AND every
    number in the claim appears in the quote. If pmid+quote pass but a number fails ->
    'partial'. Anything else -> 'unverified' with a reason.
"""

from __future__ import annotations

import re
import unicodedata

from backend.contracts import ExperimentDesign, RationaleItem

# Match standalone numeric tokens only — a digit run NOT glued to letters (so 'CHEMBL554'
# and inline ids don't leak in). Optional thousands separators and decimals.
_NUM_RE = re.compile(r"(?<![A-Za-z0-9])\d[\d,]*\.?\d*(?![A-Za-z0-9])")


def _normalise(text: str) -> str:
    """NFKC + collapsed whitespace + lowercase. Must match how abstracts are stored."""
    text = unicodedata.normalize("NFKC", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text.lower()


def _numbers(text: str) -> list[float]:
    """Extract numeric tokens, stripping thousands separators."""
    out = []
    for tok in _NUM_RE.findall(text or ""):
        tok = tok.replace(",", "")
        if tok in ("", "."):
            continue
        try:
            out.append(float(tok))
        except ValueError:
            continue
    return out


def _nums_match(claim_nums: list[float], allowed: list[float], tol: float = 0.02) -> bool:
    """Every number in the claim must equal some allowed value (within a small rel. tol
    for float formatting). Empty claim-number list trivially matches."""
    for cn in claim_nums:
        if not any(abs(cn - a) <= tol * max(abs(a), 1.0) for a in allowed):
            return False
    return True


def check_claim(
    item: RationaleItem,
    pair_activity_values: dict[str, float],
    evidence_abstracts: dict[str, str],
) -> RationaleItem:
    """Verify one claim. `pair_activity_values` maps activity_id -> value_nM for THIS
    pair; `evidence_abstracts` maps pmid -> normalised abstract text for THIS pair."""
    claim_nums = _numbers(item.claim)

    if item.evidence_type == "chembl_activity":
        aid = str(item.evidence_id)
        if aid not in pair_activity_values:
            return item.model_copy(update={
                "status": "unverified",
                "reason": f"activity {aid} not in this pair's records",
            })
        value = pair_activity_values[aid]
        if not _nums_match(claim_nums, [value]):
            return item.model_copy(update={
                "status": "unverified",
                "reason": f"claim numbers {claim_nums} != record value {value}",
            })
        return item.model_copy(update={"status": "verified", "reason": None})

    if item.evidence_type == "abstract_quote":
        pmid = str(item.evidence_id or item.pmid)
        if pmid not in evidence_abstracts:
            return item.model_copy(update={
                "status": "unverified",
                "reason": f"pmid {pmid} not in this pair's evidence set",
            })
        if not item.quote:
            return item.model_copy(update={
                "status": "unverified", "reason": "no quote provided",
            })
        abstract = evidence_abstracts[pmid]
        norm_quote = _normalise(item.quote)
        if norm_quote not in abstract:
            return item.model_copy(update={
                "status": "unverified", "reason": "quote not found in abstract",
            })
        # pmid + quote pass; now the numbers in the CLAIM must all appear in the QUOTE
        quote_nums = _numbers(item.quote)
        if not _nums_match(claim_nums, quote_nums):
            return item.model_copy(update={
                "status": "partial",
                "reason": "quote found but a claim number is absent from it",
            })
        return item.model_copy(update={"status": "verified", "reason": None})

    return item.model_copy(update={
        "status": "unverified", "reason": f"unknown evidence_type '{item.evidence_type}'",
    })


def check_citations(
    design: ExperimentDesign,
    pair: dict | None = None,
    evidence_abstracts: dict[str, str] | None = None,
) -> ExperimentDesign:
    """Check every rationale item against this design's pair evidence.

    `pair` is a demo-pair dict (for chembl_activity values); `evidence_abstracts` maps
    pmid -> normalised abstract text (for abstract_quote). Either may be None/empty.
    """
    pair_values: dict[str, float] = {}
    if pair:
        for p in pair.get("prior", {}).get("papers", []):
            pair_values[str(p["activity_id"])] = float(p["value_nM"])
    evidence_abstracts = evidence_abstracts or {}

    checked = [check_claim(item, pair_values, evidence_abstracts) for item in design.rationale]
    return design.model_copy(update={"rationale": checked})


def citation_error_rate(design: ExperimentDesign) -> float:
    """Share of claims that are not fully verified. Reported before/after checking."""
    if not design.rationale:
        return 0.0
    bad = sum(1 for r in design.rationale if r.status != "verified")
    return bad / len(design.rationale)
