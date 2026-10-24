# Dashboard (Lab Planner) — requirements

Stage 5, owner C. The researcher-facing UI. Full build brief: `frontend/BRIEF.md`.
Backend contract gaps the UI detects at runtime: `backend/DASHBOARD_GAPS.md`.

Requirements are written in EARS. R0 is the honesty baseline (BRIEF section 0); R1–R15
map one-to-one to BRIEF sections 5.1–5.15. Each requirement notes the backend data it
reads and the capability flag that unlocks it (fallbacks in BRIEF section 3.3).

## R0 — Honesty baseline (BRIEF section 0)
- R0.1 WHEN any number is shown THE SYSTEM SHALL render it through `<Num>` with a source,
  a `simulated` label, or a `derived` provenance listing its inputs.
- R0.2 IF the backend did not send a value THEN THE SYSTEM SHALL state in one plain
  sentence what is missing, and SHALL NOT invent a number, percentage, or chart.
- R0.3 WHEN model-written text is shown THE SYSTEM SHALL NOT mark it verified; only
  `RationaleItem.status` decides a badge.
- R0.4 THE SYSTEM SHALL label the robot replay as a replay of the Opentrons simulator run.
- R0.5 THE SYSTEM SHALL NOT display any third-party logo, and SHALL draw the Flex deck as a schematic.
- R0.6 THE SYSTEM SHALL handle all backend quirks in `src/api/normalize.ts` only.

## R1 — Top bar, question, settings (BRIEF 5.1)
- WHEN the user submits a question THE SYSTEM SHALL POST `/api/run` with the question,
  weights, and advanced settings (runs, seed, reader_cv).
- WHEN the server is unreachable THE SYSTEM SHALL show the server-down banner within 10 s
  and offer a recorded run.
- WHILE a run is in flight THE SYSTEM SHALL disable Run and label it "Running".

## R2 — Run progress and reveal (BRIEF 5.2)
- WHEN a run starts THE SYSTEM SHALL show all four stages as "running" with one honest line
  and SHALL NOT show fake percentages.
- WHEN the response lands THE SYSTEM SHALL reveal the stages in order, 350 ms apart.
- WHERE the async capability (B2.1) exists THE SYSTEM SHALL poll and reveal each stage as
  its report appears.
- WHEN a stage fails THE SYSTEM SHALL show its error and keep earlier stages visible.

## R3 — Safety gate (BRIEF 5.3)
- IF `blocked` is true or the safety gate did not pass THEN THE SYSTEM SHALL show only the
  blocked panel with `safety.reasons` verbatim, and SHALL leave the bench empty.

## R4 — Topic (BRIEF 5.4)
- WHEN topic data arrives THE SYSTEM SHALL draw the 2015–2024 counts, momentum scale, and
  a model card from `topic.momentum`.
- IF the counts are offline (`topic.offline` or openalex_id "T00000") THEN THE SYSTEM SHALL
  NOT draw the chart and SHALL say the numbers aren't shown.

## R5 — Less explored topics / pivot (BRIEF 5.5)
- WHERE real neighbors exist THE SYSTEM SHALL list them with a one-click pivot that moves the
  name into the question field and reruns.
- THE SYSTEM SHALL drop any neighbor with id "T00001" or a name starting "placeholder".

## R6 — Viability matrix (BRIEF 5.6)
- WHEN the user drags a weight slider THE SYSTEM SHALL recompute the total in the browser
  immediately using the backend's weighted-mean formula.
- WHERE default weights are used THE SYSTEM SHALL match the backend `matrix.total` within 1e-6.
- WHERE an axis source is `assumed` THE SYSTEM SHALL label it "Assumed value".

## R7 — Experiment design (BRIEF 5.7)
- WHEN design data arrives THE SYSTEM SHALL show the pair header, starting guess, dilution
  ladder, planned plate map, and facts, each number sourced.
- IF the pair match is "default" THEN THE SYSTEM SHALL show the worked-example notice.

## R8 — Design review / debate (BRIEF 5.8)
- WHEN rationale items arrive THE SYSTEM SHALL show one turn per item with a badge driven by
  `status`, and SHALL render `model_note` separately labelled "Model's note, not verified".
- IF any item is not verified THEN THE SYSTEM SHALL show a red summary line with jump links.
- THE SYSTEM SHALL compute the rule checks in the browser from the design.

## R9 — Robot check (BRIEF 5.9)
- WHEN sim data arrives THE SYSTEM SHALL show the simulator verdict, cost (with provenance),
  run log, and protocol access.
- IF `opentrons_version` contains "not installed" THEN THE SYSTEM SHALL show the static-check notice.

## R10 — The Bench and replay (BRIEF 5.10)
- THE SYSTEM SHALL draw the Flex deck schematic with labware from `sim.deck` or the fixed layout.
- WHERE structured steps exist THE SYSTEM SHALL replay the simulator run and, at the end, show
  the plate audit comparing final state to the plan.
- IF steps are not structured THEN THE SYSTEM SHALL disable Play with the reason.

## R11 — Uncertainty (BRIEF 5.11)
- THE SYSTEM SHALL place the whole section in a `simulated` block labelled "Simulated, seed N, M runs".
- THE SYSTEM SHALL show the p90/median headline, noise table (each row sourced), and the
  calibration coverage against the 90% mark, using server numbers only.

## R12 — Lab controls / what-if (BRIEF 5.12)
- WHILE a lab-control slider is dragged THE SYSTEM SHALL update geometry every frame and dim
  server-dependent numbers.
- WHEN the user releases a slider THE SYSTEM SHALL POST the patched design to `/api/uncertainty`
  (and `/api/simulate` when available) with a new design_id, cancel older requests, and show
  the new p90 with the old value ghosted for 1.5 s.
- THE SYSTEM SHALL enforce the BRIEF 5.12 limits in the browser so the backend never rejects a design.

## R13 — Best next changes, pin, compare (BRIEF 5.13)
- THE SYSTEM SHALL list `next_experiments` in server order with improvement and extra cost.
- WHEN "Try this change" is clicked THE SYSTEM SHALL apply `next.design` (or the parsed label)
  to the lab controls and recompute.
- THE SYSTEM SHALL plot pinned designs and suggestions on a cost-against-certainty chart.

## R14 — History and sharing (BRIEF 5.14)
- WHEN `?run={id}` or `?demo={file}` is present THE SYSTEM SHALL load that run.
- THE SYSTEM SHALL record this browser's runs in localStorage (guarded) and offer a share link.

## R15 — Provenance (BRIEF 5.15)
- THE SYSTEM SHALL open a provenance popover for every `<Num>` on hover/focus/tap, showing the
  kind, id, link (built per the BRIEF table when no url is sent), and inputs for derived values.
- IN development THE SYSTEM SHALL flag any `<Num>` without provenance (magenta outline + console warning).

## API consumed (commit d2d4406)
- `POST /api/run`, `GET /api/run/{run_id}`, `POST /api/uncertainty`, `GET /api/health`.
- All other endpoints (`/api/pairs`, `/api/simulate`, `/api/protocol/{name}`, `/api/metrics`,
  `/api/evidence/{id}`) are capability-gated — see `backend/DASHBOARD_GAPS.md`.

## Status
Steering (`.kiro/steering/ui.md`), hooks, and this spec are in place. Build order in `tasks.md`.
