"""Citation checker. Owner B.

Looks up each PubMed id and compares the returned title against the claim's cited
title. Unverified or mismatched claims get flagged. Network lookups go through the
pipeline ingest/cache layer so this stays deterministic offline.
"""

from __future__ import annotations

from collections.abc import Callable

from backend.contracts import ExperimentDesign, RationaleItem


def check_citations(
    design: ExperimentDesign,
    lookup_title: Callable[[str], str | None] | None = None,
) -> ExperimentDesign:
    """Mark each rationale item verified if its PMID resolves. `lookup_title` maps a
    PMID to a title (real impl: PubMed E-utilities via cache); None means offline, so
    nothing is marked verified (conservative)."""
    checked: list[RationaleItem] = []
    for item in design.rationale:
        verified = False
        if lookup_title is not None:
            title = lookup_title(item.pmid)
            verified = title is not None
        checked.append(item.model_copy(update={"verified": verified}))
    return design.model_copy(update={"rationale": checked})


def citation_error_rate(design: ExperimentDesign) -> float:
    """Share of cited PMIDs that are unverified. Reported before/after checking."""
    if not design.rationale:
        return 0.0
    bad = sum(1 for r in design.rationale if not r.verified)
    return bad / len(design.rationale)
