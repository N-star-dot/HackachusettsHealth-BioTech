# Dashboard (Lab Planner) — design

Architecture and data flow for the stage-5 UI. Full detail: `frontend/BRIEF.md`
(sections 3, 4, 6, 10, and Appendices A/B). This document is the architectural summary.

## Stack
React 19 + Vite + TypeScript. State: React Query (server data) + Zustand (UI state). Charts
are hand-built SVG with d3-scale/shape/array/interpolate — no chart library. Radix for the
provenance popover and sliders. CSS Modules + CSS custom properties — no Tailwind/kit.
Exact pinned versions in BRIEF section 2.

## Data flow
```
question ─▶ POST /api/run ─▶ RunResponse
                               │
          normalize.ts (the ONLY quirk-aware module)
                               │
     ┌────────────┬────────────┼─────────────┬──────────────┐
   Topic        Design        Sim        Uncertainty     (pair)
     │            │            │              │
  Notebook stages (left column)          Bench (right column)
                                          deck · replay · lab controls · readout
```

- `src/api/client.ts` — one fetch wrapper, base URL from `VITE_API_BASE`, AbortController
  timeouts (run 90s, uncertainty 30s, simulate 15s, else 10s).
- `src/api/normalize.ts` — absorbs every backend quirk (BRIEF 3.1): `pass` vs `passed`
  (→ `ok`), offline counts (openalex_id "T00000"), placeholder neighbors, assumed axes,
  formula cost, label-only next_experiments. Nothing else in the app knows these.
- `src/api/schemas.ts` — zod validation at the boundary; loose objects, dev panel on failure.
- `src/api/capabilities.ts` — reads `/openapi.json` once + optional response fields → feature
  flags. Every feature has a fallback; none blocks P0 (BRIEF 3.3).

## API adapter: today vs announced
Types are hand-written in `src/api/types.ts` (BRIEF Appendix A) until `RunResponse` appears in
`/openapi.json`, then `npm run gen:api` emits `src/api/schema.d.ts`. The adapter boundary means
backend additions (DASHBOARD_GAPS B0–B2) light up features without touching components.

## Layout (BRIEF section 4)
Two columns ≥1200px: the **notebook** (one scrolling sheet, stages in order, prose ≤68ch) and
the sticky **bench** (480px: deck, replay, lab controls, readout). One column <900px with the
bench after Design and lab controls in a bottom sheet.

## Components (BRIEF section 10)
`Num/` (the provenance primitive), `Shell/`, `Topic/`, `Matrix/`, `Design/`, `Review/`,
`Robot/`, `Bench/` (the signature replay element), `Uncertainty/`, `Controls/`. Pure logic
lives in `src/lib/*` (matrix, dilution, hill, plate, whatif, replay, audit, provenance,
format, labware, planner, hash) with no React imports — these are unit/property tested.

## Design tokens (BRIEF section 6)
All color in `src/design/tokens.css` (no raw hex in components). Archivo Variable for the
system voice (width by role), Newsreader only for paper quotes, monospace only in the protocol
viewer. Pink/blue are data colors (target activity ramp) — never UI chrome. Simulated values
sit on a hatch; assumed values use a dotted outline.

## Motion (BRIEF section 7)
The run reveal is the only automatic choreography. Everything else answers a user action.
Reduced-motion disables travel/stagger/tweens. Constants in `src/design/motion.ts`.

## Honesty invariants (enforced, not aspirational)
- A `<Num>` without provenance = a dev-build magenta outline + a failing vitest (BRIEF 5.15).
- Model text (`model_note`) never renders next to a verified badge (R0.3 / R8).
- Offline/placeholder/assumed data is detected in `normalize.ts` and labelled, never drawn as real.
