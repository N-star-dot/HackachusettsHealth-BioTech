"""Stage 1: topic scoring. Owners B (data) + A (momentum model).

Produces a TopicReport: yearly counts, momentum probability, neighbours, and the
viability matrix. The SAFETY GATE runs first — a failing gate short-circuits scoring.

This is a working stub: it runs the real safety gate and assembles a valid
TopicReport from either (a) live OpenAlex data via the pipeline, or (b) the mock
fixture when offline. Replace `_counts_from_source` and `_momentum` with the real
ingest + model as those land.
"""

from __future__ import annotations

from backend.contracts import (
    Momentum,
    Neighbor,
    SafetyGate,
    Source,
    TopicRef,
    TopicReport,
    ViabilityMatrix,
    YearCount,
)
from backend.contracts.common import SourceType
from backend.safety import check_topic_safety


def _counts_from_source(query: str) -> tuple[TopicRef, list[YearCount]]:
    """Placeholder yearly counts. Real version calls pipeline.ingest.openalex."""
    topic = TopicRef(openalex_id="T00000", name=query[:60] or "placeholder topic")
    counts = [
        YearCount(year=y, works=max(50, 800 - (2024 - y) * 40),
                  source=Source(type=SourceType.OPENALEX, id=topic.openalex_id))
        for y in range(2015, 2025)
    ]
    return topic, counts


def _momentum(counts: list[YearCount]) -> Momentum:
    """Placeholder momentum. Real version loads the trained HGB model (owner A)."""
    # naive slope-based heuristic as a stand-in for the model
    works = [c.works for c in counts]
    growing = works[-1] > works[0]
    return Momentum(p_growth=0.71 if growing else 0.35, model="hgb-v1-stub")


def score_topic(query: str, weights: dict[str, float] | None = None) -> TopicReport:
    safety: SafetyGate = check_topic_safety(query)

    topic, counts = _counts_from_source(query)
    momentum = _momentum(counts)

    weights = weights or {
        "momentum": 0.2, "novelty": 0.2, "evidence": 0.2, "automatable": 0.2, "cost_time": 0.2,
    }
    axes = {
        "momentum": momentum.p_growth,
        "novelty": 0.55,
        "evidence": 0.40,
        "automatable": 1.0,
        "cost_time": 0.62,
    }
    total = ViabilityMatrix.weighted_total(axes, weights)
    matrix = ViabilityMatrix(**axes, weights=weights, total=round(total, 6))

    neighbors = [
        Neighbor(openalex_id="T00001", name="placeholder neighbor", works_last_5y=340, p_growth=0.64),
    ]

    return TopicReport(
        query=query,
        topic=topic,
        counts_by_year=counts,
        momentum=momentum,
        neighbors=neighbors if safety.passed else [],
        matrix=matrix,
        safety=safety,
    )
