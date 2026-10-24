"""TopicReport (stage 1 output).

Built by B, momentum score added by A, shown by C.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from backend.contracts.common import SafetyGate, Source


class TopicRef(BaseModel):
    openalex_id: str
    name: str


class YearCount(BaseModel):
    year: int
    works: int = Field(..., ge=0)
    source: Source


class Momentum(BaseModel):
    """Output of the momentum model: probability the topic grows faster than typical."""

    p_growth: float = Field(..., ge=0.0, le=1.0)
    model: str = Field(..., description="Model version tag, e.g. 'hgb-v1'.")


class Neighbor(BaseModel):
    openalex_id: str
    name: str
    works_last_5y: int = Field(..., ge=0)
    p_growth: float | None = Field(default=None, ge=0.0, le=1.0)


class ViabilityMatrix(BaseModel):
    """Five axes scaled 0..1 combined into a weighted total. Weights are dashboard
    sliders and start equal. Safety is a gate, not an axis."""

    momentum: float = Field(..., ge=0.0, le=1.0)
    novelty: float = Field(..., ge=0.0, le=1.0)
    evidence: float = Field(..., ge=0.0, le=1.0)
    automatable: float = Field(..., ge=0.0, le=1.0)
    cost_time: float = Field(..., ge=0.0, le=1.0)
    weights: dict[str, float] = Field(
        default_factory=lambda: {
            "momentum": 0.2,
            "novelty": 0.2,
            "evidence": 0.2,
            "automatable": 0.2,
            "cost_time": 0.2,
        }
    )
    total: float = Field(..., ge=0.0, le=1.0)
    # Axes that could not be computed for this topic (e.g. offline OpenAlex). They are
    # excluded from `total`, and the dashboard shows them as "Unavailable offline" (H2).
    unavailable_axes: list[str] = Field(default_factory=list)
    # per-axis provenance (B0.2). Keys are axis names; values tag where each axis value
    # came from. Axes we haven't computed yet carry an 'assumed' Source.
    axis_sources: dict[str, Source] = Field(default_factory=dict)
    axis_notes: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check_total(self) -> "ViabilityMatrix":
        axes = {
            "momentum": self.momentum,
            "novelty": self.novelty,
            "evidence": self.evidence,
            "automatable": self.automatable,
            "cost_time": self.cost_time,
        }
        skip = set(self.unavailable_axes)
        num = sum(
            axes[k] * self.weights.get(k, 0) for k in axes if k not in skip
        )
        wsum = sum(w for k, w in self.weights.items() if k not in skip)
        expected = num / wsum if wsum > 0 else 0.0
        if abs(expected - self.total) > 1e-6:
            raise ValueError(
                f"matrix total {self.total} does not match weighted axes {expected:.6f}"
            )
        return self

    @staticmethod
    def weighted_total(
        axes: dict[str, float],
        weights: dict[str, float],
        unavailable_axes: list[str] | None = None,
    ) -> float:
        """Helper so producers compute `total` the same way the validator checks it.
        Axes in `unavailable_axes` are excluded from both numerator and weight sum."""
        skip = set(unavailable_axes or [])
        num = sum(axes[k] * weights.get(k, 0) for k in axes if k not in skip)
        den = sum(w for k, w in weights.items() if k not in skip)
        return num / den if den > 0 else 0.0


class TopicReport(BaseModel):
    query: str
    topic: TopicRef
    counts_by_year: list[YearCount]
    momentum: Momentum
    neighbors: list[Neighbor] = Field(default_factory=list)
    matrix: ViabilityMatrix
    safety: SafetyGate
    offline: bool = Field(
        default=False,
        description="True when OpenAlex was unreachable and counts are placeholders.",
    )
