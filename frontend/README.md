# Dashboard (stage 5) — owner C

This folder holds the researcher-facing UI. Stack is your call (React/Vite recommended;
Streamlit is a fast alternative). The backend is ready — point the frontend at it.

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
