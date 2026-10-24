# Dashboard — requirements

Stage 5. The researcher-facing UI. Owner C.

## Requirements
1. **Topic entry + viability matrix** with adjustable weight sliders (re-scores live).
2. **What-if sliders** on the design (replicates, dilution points/factor, transfer volume)
   that call `POST /api/uncertainty` and redraw fold error in real time.
3. **Run replay** of the simulated robot run from `SimResult.steps`.
4. **Source on hover** for every number — OpenAlex/PMID/ChEMBL id, spec link, or the
   `simulated, seed N` label. This is the trust feature; it is not optional.
5. **Red flag** on unverified citations.

## API it consumes
- `POST /api/run` — full pipeline for a query.
- `GET /api/run/{run_id}` — reload a persisted run.
- `POST /api/uncertainty` — rerun stage 4 for a slider-modified design.

## Status
Backend endpoints live (`backend/api/app.py`). Frontend goes in `frontend/` (stack is C's call).
