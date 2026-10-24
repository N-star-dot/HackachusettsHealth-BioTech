"""FastAPI app: the dashboard's backend. Owner C consumes these endpoints.

Endpoints:
  POST /api/run           -> run the full pipeline for a query, return all contracts
  GET  /api/run/{run_id}  -> reload a persisted run from the database
  POST /api/uncertainty   -> rerun stage 4 only for a design (what-if sliders)
  GET  /api/health        -> liveness
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.contracts import ExperimentDesign
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


class RunRequest(BaseModel):
    query: str = Field(..., min_length=1)
    weights: dict[str, float] | None = None
    runs: int = Field(default=1000, ge=1, le=5000)
    seed: int = 42
    reader_cv: float = Field(default=0.05, ge=0.0, le=0.5)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/run")
def run(req: RunRequest) -> dict:
    result = run_pipeline(
        req.query, weights=req.weights, runs=req.runs, seed=req.seed, reader_cv=req.reader_cv
    )
    return {
        "run_id": result.run_id,
        "blocked": result.blocked,
        "topic": result.topic.model_dump(by_alias=True),
        "design": result.design.model_dump() if result.design else None,
        "sim": result.sim.model_dump(by_alias=True) if result.sim else None,
        "uncertainty": result.uncertainty.model_dump() if result.uncertainty else None,
    }


@app.get("/api/run/{run_id}")
def get_run(run_id: str) -> dict:
    db = get_db()
    meta = db.get_run(run_id)
    if not meta:
        raise HTTPException(status_code=404, detail="run not found")
    return {
        "run_id": run_id,
        "meta": meta,
        "topic": db.get_report(run_id, "topic"),
        "design": db.get_report(run_id, "design"),
        "sim": db.get_report(run_id, "sim"),
        "uncertainty": db.get_report(run_id, "uncertainty"),
    }


class WhatIfRequest(BaseModel):
    design: ExperimentDesign
    runs: int = Field(default=1000, ge=1, le=5000)
    seed: int = 42
    reader_cv: float = Field(default=0.05, ge=0.0, le=0.5)


@app.post("/api/uncertainty")
def uncertainty(req: WhatIfRequest) -> dict:
    """Rerun stage 4 for a (possibly slider-modified) design. Powers the what-if UI."""
    report = run_uncertainty(req.design, runs=req.runs, seed=req.seed, reader_cv=req.reader_cv)
    report.next_experiments = plan_next_experiments(req.design, report)
    return report.model_dump()
