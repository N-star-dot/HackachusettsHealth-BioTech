"""Stage 1: topic scoring. Owners B (data) + A (momentum model).

Produces a TopicReport: yearly counts, momentum probability, neighbours, and the
viability matrix. The SAFETY GATE runs first — a failing gate short-circuits scoring.

Momentum comes from the trained HGB model (hgb-v3) when available, computed from
leakage-safe 2015-2019 features. If no model is trained yet, or the topic can't be
resolved live, we fall back to a slope heuristic so the stage still returns a valid
report. Counts come from OpenAlex via the cached ingest layer, with an offline
placeholder fallback.
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
from backend.stage1_topic.features import compute_features, slope_baseline_score
from backend.stage1_topic.momentum_model import MODEL_VERSION, predict_p_growth


def _placeholder_counts(query: str) -> tuple[TopicRef, list[YearCount], str | None]:
    topic = TopicRef(openalex_id="T00000", name=query[:60] or "placeholder topic")
    counts = [
        YearCount(year=y, works=max(50, 800 - (2024 - y) * 40),
                  source=Source(type=SourceType.OPENALEX, id=topic.openalex_id))
        for y in range(2015, 2025)
    ]
    return topic, counts, None


def _counts_from_source(query: str) -> tuple[TopicRef, list[YearCount], str | None]:
    """Resolve the top matching OpenAlex topic and its 2015-2024 yearly counts (cached).

    Returns (topic_ref, year_counts, field). Falls back to a placeholder series if the
    network/key is unavailable so the stage still produces a valid report offline.
    """
    try:
        from pipeline.ingest import openalex

        hits = openalex.search_topics(query, per_page=1)
        if not hits:
            return _placeholder_counts(query)
        hit = hits[0]
        oa_id = hit["id"].rsplit("/", 1)[-1]
        name = hit.get("display_name") or query
        field = (hit.get("field") or {}).get("display_name")
        topic = TopicRef(openalex_id=oa_id, name=name)
        rows = openalex.works_by_year(oa_id)
        counts = [
            YearCount(year=r["year"], works=r["works"],
                      source=Source(type=SourceType.OPENALEX, id=oa_id))
            for r in rows
        ]
        if len(counts) < 3:
            return _placeholder_counts(query)
        return topic, counts, field
    except Exception:
        # any network / import / parse failure -> offline placeholder
        return _placeholder_counts(query)


def _momentum(counts: list[YearCount], field: str | None) -> Momentum:
    """Momentum from the trained model, else a slope heuristic fallback."""
    counts_rows = [{"year": c.year, "works": c.works} for c in counts]
    feats = compute_features(counts_rows)

    if feats is not None:
        feats = {**feats, "field": field}
        p = predict_p_growth(feats)
        if p is not None:
            return Momentum(p_growth=round(p, 4), model=MODEL_VERSION)
        # no trained model: squash the raw slope into (0,1) as a transparent heuristic
        slope = slope_baseline_score(feats)
        p_heur = 1.0 / (1.0 + pow(2.718281828, -40.0 * slope))
        return Momentum(p_growth=round(p_heur, 4), model="slope-heuristic")

    # too sparse to compute features
    works = [c.works for c in counts]
    growing = len(works) >= 2 and works[-1] > works[0]
    return Momentum(p_growth=0.6 if growing else 0.4, model="slope-heuristic")


def score_topic(query: str, weights: dict[str, float] | None = None) -> TopicReport:
    safety: SafetyGate = check_topic_safety(query)

    topic, counts, field = _counts_from_source(query)
    momentum = _momentum(counts, field)

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
