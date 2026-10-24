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
    SEMANTIC_SCHOLAR = "semantic_scholar"
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
