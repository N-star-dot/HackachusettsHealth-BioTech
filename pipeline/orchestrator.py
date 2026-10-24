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
from backend.stage1_topic import recompute_axes, score_topic
from backend.stage2_design import check_citations, design_experiment, review_design
from backend.stage2_design.demo_pairs import (
    evidence_abstracts_for,
    get_demo_pair,
    match_pair,
    pair_names,
)
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
    pair: dict | None = None  # {label, compound_chembl_id, target_chembl_id, compound_name, target_name, match}


def _safe_title_lookup(pmid: str) -> str | None:
    """Resolve a PMID title via PubMed (cached), treating any failure as unverified.

    In offline mode an uncached PMID raises OfflineCacheMiss; a live lookup can fail
    on network errors. Either way the citation stays unverified — the conservative,
    source-honest default.
    """
    try:
        from pipeline.ingest import pubmed
        return pubmed.fetch_title(pmid)
    except Exception:  # noqa: BLE001 - any lookup failure -> treat citation as unverified
        return None


def run_pipeline(
    query: str,
    weights: dict[str, float] | None = None,
    runs: int = 1000,
    seed: int = 42,
    reader_cv: float = 0.05,
    persist: bool = True,
    target_chembl_id: str | None = None,
) -> PipelineResult:
    db = get_db() if persist else None
    run_id = run_id or (db.create_run(query) if db else "ephemeral")

    # --- stage 1: topic (safety gate inside) ---
    topic = score_topic(query, weights=weights, openalex_topic_id=openalex_topic_id)
    if db:
        db.save_report(run_id, "topic", topic)
        db.set_run_status(run_id, "topic")

    if not topic.safety.passed:
        # safety gate failed -> stop before any design work
        if db:
            db.set_run_status(run_id, "done")
        return PipelineResult(run_id, topic, None, None, None, blocked=True)

    # --- stage 2: design + citation check ---
    # Real ChEMBL prior when a target is supplied (cached); None -> placeholder prior.
    prior = None
    if target_chembl_id:
        try:
            from pipeline.ingest import chembl
            prior = chembl.prior_ic50_nM(target_chembl_id)
        except Exception:  # noqa: BLE001 - no/failed prior -> placeholder prior in designer
            prior = None
    design = design_experiment(
        topic.topic.openalex_id, prior=prior, target_chembl_id=target_chembl_id
    )
    # Verify PMIDs against PubMed (cached). Any lookup failure (offline cache miss,
    # network error, unresolved PMID) is treated as unverified — conservative and safe.
    design = check_citations(design, lookup_title=_safe_title_lookup)
    if db:
        db.save_report(run_id, "pair", pair_info)
        db.save_report(run_id, "design", design)
        db.set_run_status(run_id, "design")

    # --- stage 3: compile + simulate ---
    protocol_path = compile_design(design)
    sim = simulate_protocol(protocol_path, design)
    if db:
        db.save_report(run_id, "sim", sim)
        db.set_run_status(run_id, "sim")

    # --- stage 4: uncertainty, then the planner (saved separately so the dashboard
    #     reveals the uncertainty numbers immediately; the planner's extra Monte Carlo
    #     reruns fill in "best next changes" a moment later instead of blocking). ---
    uncertainty = run_uncertainty(design, runs=runs, seed=seed, reader_cv=reader_cv)
    if db:
        db.save_report(run_id, "uncertainty", uncertainty)
        db.set_run_status(run_id, "uncertainty")

    uncertainty.next_experiments = plan_next_experiments(design, uncertainty)
    if db:
        db.save_report(run_id, "uncertainty", uncertainty)

    # --- B2.5: Skeptic debate, settled by simulation (empty without GEMINI_API_KEY) ---
    review = review_design(
        design, uncertainty.fold_error.p90, runs=runs, seed=seed, reader_cv=reader_cv
    )
    if review:
        design = design.model_copy(update={"review": review})
        if db:
            db.save_report(run_id, "design", design)

    # --- B1.5: recompute the four fixed matrix axes now that stages 2-3 have run ---
    topic = recompute_axes(topic, design, sim)
    if db:
        db.save_report(run_id, "topic", topic)
        db.set_run_status(run_id, "done")

    return PipelineResult(run_id, topic, design, sim, uncertainty, pair=pair_info)
