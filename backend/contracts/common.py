"""Shared contract pieces: the Source provenance tag and the Safety gate."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    """Where a number came from. `simulated` is the only non-real provenance and
    must only appear inside blocks explicitly labelled as simulated."""

    OPENALEX = "openalex"
    PUBMED = "pubmed"
    CHEMBL_ACTIVITY = "chembl_activity"
    PAPER = "paper"  # a cited DOI, e.g. the Kalliokoski noise paper
    SPEC = "spec"  # a published vendor spec table, e.g. Opentrons pipettes
    SIMULATOR = "simulator"  # the Opentrons simulator
    SIMULATED = "simulated"  # synthetic values from our own Monte Carlo
    ASSUMED = "assumed"  # a value we chose ourselves, not measured from this topic


class Source(BaseModel):
    """Provenance tag. Every real number in the contracts carries one so the UI can
    show 'source on hover' and the citation checker can verify it."""

    type: SourceType
    id: str = Field(..., description="Identifier within the source, e.g. an OpenAlex topic id, PMID, ChEMBL activity id, DOI, or spec table name.")
    url: str | None = Field(default=None, description="Optional direct link to the source.")


class SafetyGate(BaseModel):
    """Pass/fail gate that runs BEFORE any scoring. A failing gate blocks the topic
    regardless of how high its other axes score — safety is a gate, not an axis."""

    passed: bool = Field(..., alias="pass")
    reasons: list[str] = Field(default_factory=list, description="Why it failed, empty when it passed.")

    model_config = {"populate_by_name": True}


def source_url(source_type: "SourceType | str", id_: str) -> str | None:
    """Build the canonical link for a source kind + id (B1.6). Links point at
    human-viewable pages, not raw API/JSON endpoints. None when there is no meaningful
    link (simulator, simulated, assumed)."""
    t = source_type.value if isinstance(source_type, SourceType) else str(source_type)
    if t == SourceType.OPENALEX.value:
        if id_.startswith("T"):
            # the openalex.org website page, not the api.openalex.org JSON
            return f"https://openalex.org/{id_}"
        return None  # 'reference: N topics' etc. have no single link
    if t == SourceType.CHEMBL_ACTIVITY.value:
        first = id_.split(",")[0].strip()
        if first and first.lower() not in ("none", "placeholder"):
            # human-viewable ChEMBL interface (an activity id), not the .json endpoint
            return f"https://www.ebi.ac.uk/chembl/explore/activities/{first}"
        return None
    if t == SourceType.PUBMED.value:
        return f"https://pubmed.ncbi.nlm.nih.gov/{id_}/"
    if t == SourceType.PAPER.value:
        doi = id_[4:] if id_.startswith("doi:") else id_
        return f"https://doi.org/{doi}"
    if t == SourceType.SPEC.value:
        return "https://docs.opentrons.com/flex/system-description/pipettes/"
    return None  # simulator, simulated, assumed, semantic_scholar(default)


def chembl_compound_url(compound_chembl_id: str) -> str | None:
    """Human-viewable ChEMBL compound report card (used for the IC50 prior's link)."""
    cid = compound_chembl_id.strip()
    if cid and cid.upper().startswith("CHEMBL"):
        return f"https://www.ebi.ac.uk/chembl/explore/compound/{cid}"
    return None


def chembl_document_url(document_chembl_id: str | None) -> str | None:
    """Human-viewable ChEMBL document (paper) report card: shows the paper's title and DOI.
    Used for citation links so each rationale item opens its source paper, not a broken
    activity page."""
    did = (document_chembl_id or "").strip()
    if did and did.upper().startswith("CHEMBL"):
        return f"https://www.ebi.ac.uk/chembl/explore/document/{did}"
    return None
