"""ExperimentDesign (stage 2 output).

The Designer LLM writes this as JSON (never code). The compiler and the uncertainty
engine read it. Every literature claim carries a PubMed id and a verified flag.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from backend.contracts.common import Source


class Assay(BaseModel):
    type: str = Field(default="dose_response")
    readout: str = Field(default="percent_activity")
    target_chembl_id: str
    compound_chembl_id: str


class PriorIC50(BaseModel):
    """Starting guess from ChEMBL measurements."""

    median_nM: float = Field(..., gt=0)
    n_measurements: int = Field(..., ge=1)
    spread_log10: float = Field(..., ge=0, description="Lab-to-lab spread in log10 units.")
    source: Source


class Dilution(BaseModel):
    top_nM: float = Field(..., gt=0)
    factor: float = Field(..., gt=1, description="Serial dilution factor, e.g. 3.")
    points: int = Field(..., ge=2)

    def bottom_nM(self) -> float:
        return self.top_nM / (self.factor ** (self.points - 1))

    def log10_span_each_side(self, prior_median_nM: float) -> float:
        """How many log10 units the range covers on each side of the prior median.
        The Skeptic wants >= 2 log units each side."""
        import math

        return min(
            math.log10(self.top_nM / prior_median_nM),
            math.log10(prior_median_nM / self.bottom_nM()),
        )


class Controls(BaseModel):
    positive_wells: int = Field(..., ge=0)
    negative_wells: int = Field(..., ge=0)


class Plate(BaseModel):
    labware: str = "corning_96_wellplate_360ul_flat"
    layout: str = "randomized"


class Volumes(BaseModel):
    transfer: float = Field(..., gt=0, description="µL transferred per step.")
    diluent: float = Field(..., gt=0, description="µL diluent per well.")


class RationaleItem(BaseModel):
    """One piece of evidence supporting the design.

    SECURITY MODEL: only text that code can prove is ever marked verified. Free text the
    LLM wrote in its own words NEVER gets a green badge, because code cannot prove a
    paraphrase matches its source, nor catch negation or unit swaps.

      * chembl_activity — `claim` is re-rendered by code from the record itself (no free
        text survives), verified iff the activity id belongs to the pair.
      * abstract_quote  — the VERIFIED thing is `quote` (an exact run of whole sentences
        from the cited abstract). `model_note` is the LLM's own wording, shown separately
        and NEVER verified.

    Fields are additive with defaults so pre-existing mocks still validate.
    """

    claim: str = Field(
        default="",
        description="For chembl_activity: a code-rendered sentence. For abstract_quote: "
                    "the model's own note (NOT verified) — surfaced for the reader only.",
    )
    pmid: str = ""
    evidence_type: str = Field(
        default="chembl_activity",
        description="'chembl_activity' or 'abstract_quote'.",
    )
    evidence_id: str = Field(
        default="",
        description="ChEMBL activity id (chembl_activity) or the PMID (abstract_quote).",
    )
    quote: str | None = Field(
        default=None,
        description="For abstract_quote: the exact sentence(s) from the abstract that are "
                    "verified. This, not `claim`, is what a green badge attests to.",
    )
    model_note: str | None = Field(
        default=None,
        description="The LLM's own paraphrase/interpretation. NEVER verified — display as "
                    "'model's note, not verified'.",
    )
    status: str = Field(
        default="unverified",
        description="'verified', 'partial', or 'unverified' — set by the checker. For "
                    "abstract_quote this is the status of the QUOTE, not the model_note.",
    )
    reason: str | None = Field(default=None, description="Why it isn't fully verified.")
    verified: bool = Field(
        default=False, description="Kept for back-compat; equals (status == 'verified')."
    )

    @model_validator(mode="after")
    def _sync_verified(self) -> "RationaleItem":
        object.__setattr__(self, "verified", self.status == "verified")
        return self


class ExperimentDesign(BaseModel):
    design_id: str
    topic_id: str
    assay: Assay
    prior_ic50: PriorIC50
    dilution: Dilution
    replicates: int = Field(..., ge=1)
    controls: Controls
    plate: Plate
    volumes_uL: Volumes
    pipette: str = "flex_1channel_1000"
    tiprack: str = "opentrons_flex_96_tiprack_200ul"
    rationale: list[RationaleItem] = Field(default_factory=list)
    notes: list[str] = Field(
        default_factory=list,
        description="Design-level notes for the UI, e.g. 'top_nM capped at 100000 nM'.",
    )

    @model_validator(mode="after")
    def _warn_small_transfer(self) -> "ExperimentDesign":
        # Not a hard failure (the Skeptic handles it), but <1µL transfers are the
        # one regime where robot error rivals biology, so we surface it.
        if self.volumes_uL.transfer < 1.0:
            object.__setattr__(self, "_transfer_warning", True)
        return self
