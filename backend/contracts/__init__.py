"""Data contracts shared between all workstreams.

These four models (plus their shared pieces) are the *contract* between the five
stages. Every workstream builds against these, and mocks each other's output, so
nobody waits. Changing a field here is a team-level decision — do it in the spec
first (.kiro/specs/data-contracts), then here.

Rule enforced by these models: every number is either attached to a `Source`, or
lives inside a block explicitly labelled `simulated`.
"""

from backend.contracts.common import Source, SourceType, SafetyGate
from backend.contracts.topic_report import (
    TopicReport,
    TopicRef,
    YearCount,
    Momentum,
    Neighbor,
    ViabilityMatrix,
)
from backend.contracts.experiment_design import (
    ExperimentDesign,
    Assay,
    PriorIC50,
    Dilution,
    Controls,
    Plate,
    Volumes,
    RationaleItem,
)
from backend.contracts.sim_result import (
    SimResult,
    SimulatorInfo,
    CostBreakdown,
    ProtocolStep,
    StepLocation,
    DeckSlot,
)
from backend.contracts.uncertainty_report import (
    UncertaintyReport,
    NoiseModel,
    FoldError,
    Calibration,
    NextExperiment,
)

__all__ = [
    "Source",
    "SourceType",
    "SafetyGate",
    "TopicReport",
    "TopicRef",
    "YearCount",
    "Momentum",
    "Neighbor",
    "ViabilityMatrix",
    "ExperimentDesign",
    "Assay",
    "PriorIC50",
    "Dilution",
    "Controls",
    "Plate",
    "Volumes",
    "RationaleItem",
    "SimResult",
    "SimulatorInfo",
    "CostBreakdown",
    "ProtocolStep",
    "StepLocation",
    "DeckSlot",
    "UncertaintyReport",
    "NoiseModel",
    "FoldError",
    "Calibration",
    "NextExperiment",
]
