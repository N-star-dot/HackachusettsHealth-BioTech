"""FastAPI app: the dashboard's backend. Owner C consumes these endpoints.

Endpoints:
  POST /api/run           -> run the full pipeline for a query, return all contracts
  GET  /api/run/{run_id}  -> reload a persisted run from the database
  POST /api/uncertainty   -> rerun stage 4 only for a design (what-if sliders)
  GET  /api/health        -> liveness

Every route declares a `response_model`, so /openapi.json carries full schemas and the
frontend can generate types. GET /api/run/{run_id} validates each stored payload through
its contract model before returning, so a reloaded run has exactly the same JSON shape as
a fresh POST (alias fields like safety.pass / simulator.pass, not the stored field names).
"""

from __future__ import annotations

from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.contracts import (
    ExperimentDesign,
    SimResult,
    TopicReport,
    UncertaintyReport,
)
from backend.stage4_uncertainty import plan_next_experiments, run_uncertainty
from database import get_db
from pipeline import run_pipeline

app = FastAPI(title="HackachusettsHealth-BioTech API", version="0.1.0")

# Dashboard runs on a different port in dev; allow it.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- response models (one JSON shape per run) ---------------------------------
class HealthResponse(BaseModel):
    status: str


class PairInfo(BaseModel):
    label: str
    compound_chembl_id: str
    target_chembl_id: str
    compound_name: str
    target_name: str
    match: Literal["user", "query", "default"]


class RunResponse(BaseModel):
    run_id: str
    blocked: bool
    status: str = "done"
    pair: PairInfo | None = None
    topic: TopicReport | None = None
    design: ExperimentDesign | None = None
    sim: SimResult | None = None
    uncertainty: UncertaintyReport | None = None


class RunMeta(BaseModel):
    run_id: str
    query: str
    created_at: str
    status: str


class RunRecord(RunResponse):
    meta: RunMeta


# --- requests -----------------------------------------------------------------
class RunRequest(BaseModel):
    query: str = Field(..., min_length=1)
    weights: dict[str, float] | None = None
    runs: int = Field(default=1000, ge=1, le=5000)
    seed: int = 42
    reader_cv: float = Field(default=0.05, ge=0.0, le=0.5)
    compound_chembl_id: str | None = None


class WhatIfRequest(BaseModel):
    design: ExperimentDesign
    runs: int = Field(default=1000, ge=1, le=5000)
    seed: int = 42
    reader_cv: float = Field(default=0.05, ge=0.0, le=0.5)


# --- routes -------------------------------------------------------------------
@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/api/pairs")
def pairs() -> list[dict]:
    """The prepared compound-target pairs the designer can use, with their priors.

    Untyped list for now (the shape mirrors data/demo/demo_pairs.json); the frontend
    reads label, ids, names, and prior {median_nM, spread_log10, n_papers, papers}.
    """
    from backend.stage2_design.demo_pairs import load_demo_pairs, pair_names

    out = []
    for p in load_demo_pairs():
        prior = p.get("prior", {})
        compound_name, target_name = pair_names(p)
        out.append({
            "label": p["label"],
            "compound_chembl_id": p["compound_chembl_id"],
            "target_chembl_id": p["target_chembl_id"],
            "compound_name": compound_name,
            "target_name": target_name,
            "prior": {
                "median_nM": prior.get("median_nM"),
                "spread_log10": prior.get("spread_log10"),
                "n_papers": prior.get("n_papers"),
                "papers": prior.get("papers", []),
            },
        })
    return out


@app.post("/api/run", response_model=RunResponse)
def run(req: RunRequest) -> RunResponse:
    result = run_pipeline(
        req.query, weights=req.weights, runs=req.runs, seed=req.seed,
        reader_cv=req.reader_cv, compound_chembl_id=req.compound_chembl_id,
    )
    return RunResponse(
        run_id=result.run_id,
        blocked=result.blocked,
        pair=PairInfo(**result.pair) if result.pair else None,
        topic=result.topic,
        design=result.design,
        sim=result.sim,
        uncertainty=result.uncertainty,
    )


@app.get("/api/run/{run_id}", response_model=RunRecord)
def get_run(run_id: str) -> RunRecord:
    db = get_db()
    meta = db.get_run(run_id)
    if not meta:
        raise HTTPException(status_code=404, detail="run not found")

    # Validate each stored payload through its contract so FastAPI dumps it by alias,
    # giving the same JSON shape as POST /api/run (pass, not passed).
    def _load(stage: str, model):
        raw = db.get_report(run_id, stage)
        return model.model_validate(raw) if raw is not None else None

    raw_pair = db.get_report(run_id, "pair")
    return RunRecord(
        run_id=run_id,
        blocked=False,
        status=meta.get("status", "done"),
        pair=PairInfo(**raw_pair) if raw_pair else None,
        topic=_load("topic", TopicReport),
        design=_load("design", ExperimentDesign),
        sim=_load("sim", SimResult),
        uncertainty=_load("uncertainty", UncertaintyReport),
        meta=RunMeta(
            run_id=meta["run_id"],
            query=meta["query"],
            created_at=meta["created_at"],
            status=meta["status"],
        ),
    )


@app.post("/api/uncertainty", response_model=UncertaintyReport)
def uncertainty(req: WhatIfRequest) -> UncertaintyReport:
    """Rerun stage 4 for a (possibly slider-modified) design. Powers the what-if UI."""
    report = run_uncertainty(req.design, runs=req.runs, seed=req.seed, reader_cv=req.reader_cv)
    report.next_experiments = plan_next_experiments(req.design, report)
    return report
