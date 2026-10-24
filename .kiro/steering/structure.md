# Project structure & ownership

Five stages, each handing the next a JSON contract (see `backend/contracts`). Three
code owners (A, B, C) plus a teammate owning the pipeline.

```
backend/
  contracts/        # THE CONTRACTS — shared by everyone. Change via spec first.
  safety/           # safety gate (runs before scoring)
  stage1_topic/     # topic scoring            -> TopicReport        (B data, A momentum)
  stage2_design/    # designer LLM + citation  -> ExperimentDesign   (B)
  stage3_protocol/  # fixed-template compiler + Opentrons sim -> SimResult (B)
  stage4_uncertainty/ # Monte Carlo + calibration + planner -> UncertaintyReport (A)
  api/              # FastAPI app for the dashboard
pipeline/           # TEAMMATE: ingest/ (cached API clients) + orchestrator.py
database/           # SQLite schema + access layer (api cache + runs + reports)
frontend/           # dashboard (C)
mocks/              # one sample JSON per contract — build against these, never wait
scripts/            # demo, eval_metrics, init_db
protocols/          # generated Opentrons .py files (gitignored output)
tests/              # smoke + mock-validation tests
```

## Stage ownership
| Stage | Output | Owner |
|-------|--------|-------|
| 1 Topic scoring | `TopicReport` | B + A |
| 2 Experiment design | `ExperimentDesign` | B |
| 3 Protocol + check | `SimResult` | B |
| 4 Uncertainty engine | `UncertaintyReport` | A |
| 5 Dashboard | live demo | C |
| Pipeline (ingest + orchestration) | cached data, run persistence | teammate |

## Working agreement
- Agree contracts by **11:00 AM**, commit them as Kiro specs, then **mock each other's
  output** so nobody waits.
- Every stage reads/writes only its contract + the DB. No stage imports another stage's
  internals — only the orchestrator wires them together.
