# Dashboard (stage 5) — owner C

The researcher-facing UI: React 18 + Vite + TypeScript. The visual design is defined by a
custom design system for the "Hackachusetts Research Dashboard"; colors and type are mirrored as tokens at
the top of `src/styles.css`.

## Run it
```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```
- **Mocks** (default, top-right switch): loads `../mocks/*.json`, no backend needed.
- **Live API**: calls the FastAPI backend through Vite's `/api` proxy to `127.0.0.1:8000`,
  and reruns `POST /api/uncertainty` as the what-if sliders move.

`npm run typecheck` type-checks; `npm run build` writes `dist/`.

## Layout
- `src/types.ts` — TypeScript mirrors of `backend/contracts`. Update when a contract changes.
- `src/api.ts` — mock loader and API calls.
- `src/components/Sourced.tsx` — the source-on-hover wrapper. Wrap every displayed number in it;
  a number with no source renders red.
- `ViabilityMatrix`, `TopicPanel`, `WhatIf`, `RunReplay`, `SidePanels` (run cost, evidence).

The replay falls back to demo steps generated from the design when `SimResult.steps` has
fewer than two entries (the mock has one); it is labelled "Demo steps from design".

## Backend contract
Run the API:
```bash
uvicorn backend.api:app --reload   # http://127.0.0.1:8000  (docs at /docs)
```

Endpoints:
- `POST /api/run` body `{ "query": "...", "weights": {...}?, "runs": 1000, "seed": 42 }`
  returns `{ run_id, blocked, topic, design, sim, uncertainty }`.
- `GET  /api/run/{run_id}` reloads a persisted run.
- `POST /api/uncertainty` body `{ "design": <ExperimentDesign>, "runs":1000, "seed":42 }`
  reruns stage 4 for what-if sliders.

Contract shapes are in `backend/contracts` and sample payloads in `mocks/`. Build against
the mocks first — you don't need the backend running to start the UI.

## Must-have UI features (see .kiro/specs/dashboard)
1. Viability matrix with live weight sliders.
2. What-if sliders -> `POST /api/uncertainty` -> redraw fold error.
3. Robot run replay from `SimResult.steps`.
4. **Source on hover for every number** (the trust feature).
5. Red flag on unverified citations.
