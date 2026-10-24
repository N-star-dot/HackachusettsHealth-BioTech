"""SimResult (stage 3 output).

The compiler + Opentrons simulator wrapper produce this. The dashboard replay reads
the steps.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


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


class ProtocolStep(BaseModel):
    i: int = Field(..., ge=0)
    action: str
    uL: float | None = None
    labware: str | None = None
    well: str | None = None


class SimResult(BaseModel):
    design_id: str
    protocol_file: str
    simulator: SimulatorInfo
    cost: CostBreakdown
    steps: list[ProtocolStep] = Field(default_factory=list)
