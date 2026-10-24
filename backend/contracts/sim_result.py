"""SimResult (stage 3 output).

The compiler + Opentrons simulator wrapper produce this. The dashboard replay reads
the steps.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from backend.contracts.common import Source


class SimulatorInfo(BaseModel):
    passed: bool = Field(..., alias="pass")
    error: str | None = None
    log_lines: int = Field(default=0, ge=0)
    seconds: float = Field(default=0.0, ge=0)
    opentrons_version: str = "10.1.0"

    model_config = {"populate_by_name": True}


class CostBreakdown(BaseModel):
    tips: int = Field(..., ge=0)
    compound_uL: float = Field(..., ge=0)
    plates: int = Field(..., ge=0)
    robot_steps: int = Field(..., ge=0)
    source: "Source | None" = None  # B0.5: simulator (counted) or assumed (formula)


class ProtocolStep(BaseModel):
    i: int = Field(..., ge=0)
    action: str
    uL: float | None = None
    labware: str | None = None
    well: str | None = None
    # structured fields for the dashboard replay (B0.4), all optional with defaults
    level: int = 0
    text: str = ""
    slot: str | None = None
    source: "StepLocation | None" = None
    dest: "StepLocation | None" = None
    repetitions: int | None = None


class StepLocation(BaseModel):
    slot: str | None = None
    well: str | None = None
    labware: str | None = None


class DeckSlot(BaseModel):
    slot: str
    load_name: str
    display_name: str
    role: str = Field(..., description="'tips' | 'plate' | 'reservoir' | 'trash'.")
    contents: dict[str, str] = Field(default_factory=dict)


class SimResult(BaseModel):
    design_id: str
    protocol_file: str
    simulator: SimulatorInfo
    cost: CostBreakdown
    steps: list[ProtocolStep] = Field(default_factory=list)
    deck: list[DeckSlot] = Field(default_factory=list)  # B0.4


ProtocolStep.model_rebuild()
