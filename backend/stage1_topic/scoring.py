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


def _counts_url(openalex_id: str) -> str:
    """The exact OpenAlex query works_by_year makes (B1.6)."""
    return (f"https://api.openalex.org/works?filter=topics.id:{openalex_id},"
            f"from_publication_date:2015-01-01,to_publication_date:2024-12-31"
            f"&group_by=publication_year")


def _placeholder_counts(query: str) -> tuple[TopicRef, list[YearCount], str | None]:
    """Offline fallback. The invented series is labelled SIMULATED, never openalex, so the
    dashboard can detect it and refuse to draw it as real data."""
    topic = TopicRef(openalex_id="T00000", name=query[:60] or "placeholder topic")
    counts = [
        YearCount(year=y, works=max(50, 800 - (2024 - y) * 40),
                  source=Source(type=SourceType.SIMULATED, id="offline-placeholder"))
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
                      source=Source(type=SourceType.OPENALEX, id=oa_id, url=_counts_url(oa_id)))
            for r in rows
        ]
        if len(counts) < 3:
            return _placeholder_counts(query)
        return topic, counts, field
    except Exception:
        # any network / import / parse failure -> offline placeholder
        return _placeholder_counts(query)


def _counts_by_id(openalex_id: str, query: str) -> tuple[TopicRef, list[YearCount], str | None]:
    """Resolve a topic directly by OpenAlex id (B2.2), skipping the keyword search."""
    try:
        from pipeline.ingest import openalex
        from pipeline.ingest.http_cache import cached_get_json

        short = openalex_id.rsplit("/", 1)[-1]
        body = cached_get_json("openalex", f"https://api.openalex.org/topics/{short}")
        name = body.get("display_name") or query
        field = (body.get("field") or {}).get("display_name")
        topic = TopicRef(openalex_id=short, name=name)
        rows = openalex.works_by_year(short)
        counts = [
            YearCount(year=r["year"], works=r["works"],
                      source=Source(type=SourceType.OPENALEX, id=short, url=_counts_url(short)))
            for r in rows
        ]
        if len(counts) < 3:
            return _placeholder_counts(query)
        return topic, counts, field
    except Exception:
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


def score_topic(query: str, weights: dict[str, float] | None = None,
                openalex_topic_id: str | None = None) -> TopicReport:
    safety: SafetyGate = check_topic_safety(query)

    if openalex_topic_id:
        topic, counts, field = _counts_by_id(openalex_topic_id, query)
    else:
        topic, counts, field = _counts_from_source(query)
    offline = topic.openalex_id == "T00000"

    if offline:
        # don't score an invented series with the model — say so plainly
        momentum = Momentum(p_growth=0.5, model="offline-placeholder")
    else:
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
    # H2: offline OpenAlex means momentum and novelty can't be computed from real counts.
    # Keep placeholder floats to satisfy the contract, but exclude them from the total and
    # flag them so the dashboard shows "Unavailable offline".
    unavailable_axes = ["momentum", "novelty"] if offline else []
    total = ViabilityMatrix.weighted_total(axes, weights, unavailable_axes)

    # per-axis provenance (B0.2). Momentum traces to the model + OpenAlex counts; the
    # other four are fixed priors until B1.5 computes them, so they carry 'assumed'.
    axis_sources: dict[str, Source] = {
        "novelty": Source(type=SourceType.ASSUMED, id="fixed-prior"),
        "evidence": Source(type=SourceType.ASSUMED, id="fixed-prior"),
        "automatable": Source(type=SourceType.ASSUMED, id="fixed-prior"),
        "cost_time": Source(type=SourceType.ASSUMED, id="fixed-prior"),
    }
    axis_notes: dict[str, str] = {
        k: "Fixed value, not computed from this topic yet"
        for k in ("novelty", "evidence", "automatable", "cost_time")
    }
    if not offline:
        axis_sources["momentum"] = Source(
            type=SourceType.OPENALEX, id=topic.openalex_id, url=_counts_url(topic.openalex_id)
        )
        axis_notes["momentum"] = (
            f"Trained model {MODEL_VERSION} scored this topic's 2015-2024 OpenAlex counts"
        )
    else:
        # H2: OpenAlex was unreachable, so momentum and novelty are not computed from real
        # data. Label them plainly; the dashboard excludes them from the total.
        axis_notes["momentum"] = "Unavailable: OpenAlex was unreachable"
        axis_notes["novelty"] = "Unavailable: OpenAlex was unreachable"

    matrix = ViabilityMatrix(
        **axes, weights=weights, total=round(total, 6),
        unavailable_axes=unavailable_axes,
        axis_sources=axis_sources, axis_notes=axis_notes,
    )

    # Real neighbors (B2.2): sibling topics in the same subfield, less crowded, scored.
    neighbors: list = [] if offline else _real_neighbors(query, topic, counts)

    return TopicReport(
        query=query,
        topic=topic,
        counts_by_year=counts,
        momentum=momentum,
        neighbors=neighbors,
        matrix=matrix,
        safety=safety,
        offline=offline,
    )


# --- B1.5: compute the four fixed axes once stages 2 and 3 have run ----------

def _topic_works_2020_2024(openalex_id: str) -> int | None:
    """2020-2024 works total for a topic from the cached works_by_year response, or None."""
    try:
        from pipeline.ingest import openalex

        rows = openalex.works_by_year(openalex_id)  # cached; no network if warm
        return sum(r["works"] for r in rows if 2020 <= r["year"] <= 2024)
    except Exception:
        return None


def _reference_novelty(topic: TopicRef) -> tuple[float, Source, str] | None:
    """novelty = share of reference (training) topics with MORE 2020-2024 works than this
    topic. Reference set = topic_features rows. Returns (value, source, note) or None if
    the cache can't supply the counts."""
    try:
        from database import get_db

        rows = get_db().all_topic_features()
    except Exception:
        return None
    if not rows:
        return None

    this_total = _topic_works_2020_2024(topic.openalex_id)
    if this_total is None:
        return None

    more = 0
    counted = 0
    for r in rows:
        ref_total = _topic_works_2020_2024(r["openalex_id"])
        if ref_total is None:
            continue
        counted += 1
        if ref_total > this_total:
            more += 1
    if counted == 0:
        return None
    novelty = more / counted
    return (
        round(novelty, 4),
        Source(type=SourceType.OPENALEX, id=f"reference: {counted} topics"),
        "Share of reference topics with more 2020-2024 works than this one",
    )


def recompute_axes(report: TopicReport, design, sim) -> TopicReport:
    """Recompute novelty/evidence/automatable/cost_time from the design + sim (B1.5) and
    return an updated TopicReport. Momentum and weights are preserved; the total is
    recomputed with ViabilityMatrix.weighted_total."""
    m = report.matrix
    axes = {
        "momentum": m.momentum,
        "novelty": m.novelty,
        "evidence": m.evidence,
        "automatable": m.automatable,
        "cost_time": m.cost_time,
    }
    axis_sources = dict(m.axis_sources)
    axis_notes = dict(m.axis_notes)

    # novelty (OpenAlex reference set; stays 'assumed' if the cache can't supply it)
    nov = _reference_novelty(report.topic)
    if nov is not None:
        axes["novelty"], axis_sources["novelty"], axis_notes["novelty"] = nov

    # evidence = min(1, n_papers / 20)
    if design is not None:
        n_papers = design.prior_ic50.n_measurements
        axes["evidence"] = round(min(1.0, n_papers / 20.0), 4)
        axis_sources["evidence"] = design.prior_ic50.source
        axis_notes["evidence"] = "20 or more independent papers counts as full evidence (our threshold)"

    # automatable = 1.0 if the simulator passed else 0.0
    if sim is not None:
        axes["automatable"] = 1.0 if sim.simulator.passed else 0.0
        axis_sources["automatable"] = Source(type=SourceType.SIMULATOR, id=sim.protocol_file)
        axis_notes["automatable"] = "1 if the protocol passed the Opentrons simulator, else 0"

    # cost_time = 1 - min(1, tips / 96)
    if sim is not None:
        axes["cost_time"] = round(1.0 - min(1.0, sim.cost.tips / 96.0), 4)
        axis_sources["cost_time"] = Source(type=SourceType.SIMULATOR, id=sim.protocol_file)
        axis_notes["cost_time"] = "Share of one 96-tip rack left unused"

    # Carry forward axes the first pass could not compute (H2 offline). If novelty just
    # became computable here, drop it from the unavailable set.
    unavailable_axes = list(m.unavailable_axes)
    if nov is not None and "novelty" in unavailable_axes:
        unavailable_axes.remove("novelty")

    total = ViabilityMatrix.weighted_total(axes, m.weights, unavailable_axes)
    new_matrix = ViabilityMatrix(
        **axes, weights=m.weights, total=round(total, 6),
        unavailable_axes=unavailable_axes,
        axis_sources=axis_sources, axis_notes=axis_notes,
    )
    return report.model_copy(update={"matrix": new_matrix})


# --- B2.2: real neighbors (shift to a less explored topic) -------------------

def _works_2020_2024_and_feats(openalex_id: str) -> tuple[int, dict | None] | None:
    """(2020-2024 works total, features) for a topic from cached counts, or None."""
    try:
        from pipeline.ingest import openalex

        rows = openalex.works_by_year(openalex_id)
    except Exception:
        return None
    if not rows:
        return None
    total = sum(r["works"] for r in rows if 2020 <= r["year"] <= 2024)
    feats = compute_features([{"year": r["year"], "works": r["works"]} for r in rows])
    return total, feats


def _real_neighbors(query: str, topic: TopicRef, counts: list[YearCount], top_k: int = 5) -> list:
    """Sibling topics in the same subfield, keeping those less crowded (fewer 2020-2024
    works) than the query topic, scored by the momentum model, top_k by p_growth."""
    try:
        from pipeline.ingest import openalex

        hits = openalex.search_topics(query, per_page=1)
        if not hits:
            return []
        subfield = (hits[0].get("subfield") or {}).get("id")
        field = (hits[0].get("field") or {}).get("display_name")
        if not subfield:
            return []
        siblings = openalex.sibling_topics(subfield)
    except Exception:
        return []

    this_total = sum(c.works for c in counts if 2020 <= c.year <= 2024)

    scored: list[tuple[float, Neighbor]] = []
    for s in siblings:
        if s["openalex_id"] == topic.openalex_id:
            continue
        got = _works_2020_2024_and_feats(s["openalex_id"])
        if got is None:
            continue
        total, feats = got
        if total >= this_total:  # keep only LESS crowded topics
            continue
        p = None
        if feats is not None:
            p = predict_p_growth({**feats, "field": s.get("field") or field})
        scored.append((
            p if p is not None else 0.0,
            Neighbor(openalex_id=s["openalex_id"], name=s["name"],
                     works_last_5y=total, p_growth=round(p, 4) if p is not None else None),
        ))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [n for _, n in scored[:top_k]]
