"""End-to-end orchestrator: query -> TopicReport -> ExperimentDesign -> SimResult ->
UncertaintyReport, persisting each contract to the database under one run_id.

This is the single entry point the dashboard/API calls. It is deliberately linear and
readable so judges can trace one researcher query through all five stages.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.contracts import (
    ExperimentDesign,
    SimResult,
    TopicReport,
    UncertaintyReport,
)
from backend.stage1_topic import score_topic
from backend.stage2_design import check_citations, design_experiment
from backend.stage3_protocol import compile_design, simulate_protocol
from backend.stage4_uncertainty import plan_next_experiments, run_uncertainty
from database import get_db


@dataclass
class PipelineResult:
    run_id: str
    topic: TopicReport
    design: ExperimentDesign | None
    sim: SimResult | None
    uncertainty: UncertaintyReport | None
    blocked: bool = False


def run_pipeline(
    query: str,
    weights: dict[str, float] | None = None,
    runs: int = 1000,
    seed: int = 42,
    reader_cv: float = 0.05,
    persist: bool = True,
) -> PipelineResult:
    db = get_db() if persist else None
    run_id = db.create_run(query) if db else "ephemeral"

    # --- stage 1: topic (safety gate inside) ---
    topic = score_topic(query, weights=weights)
    if db:
        db.save_report(run_id, "topic", topic)
        db.set_run_status(run_id, "topic")

    if not topic.safety.passed:
        # safety gate failed -> stop before any design work
        if db:
            db.set_run_status(run_id, "done")
        return PipelineResult(run_id, topic, None, None, None, blocked=True)

    # --- stage 2: design + citation check ---
    design = design_experiment(topic.topic.openalex_id)
    design = check_citations(design)  # offline -> leaves unverified; pass lookup when online
    if db:
        db.save_report(run_id, "design", design)
        db.set_run_status(run_id, "design")

    # --- stage 3: compile + simulate ---
    protocol_path = compile_design(design)
    sim = simulate_protocol(protocol_path, design)
    if db:
        db.save_report(run_id, "sim", sim)
        db.set_run_status(run_id, "sim")

    # --- stage 4: uncertainty + planner ---
    uncertainty = run_uncertainty(design, runs=runs, seed=seed, reader_cv=reader_cv)
    uncertainty.next_experiments = plan_next_experiments(design, uncertainty)
    if db:
        db.save_report(run_id, "uncertainty", uncertainty)
        db.set_run_status(run_id, "done")

    return PipelineResult(run_id, topic, design, sim, uncertainty)
