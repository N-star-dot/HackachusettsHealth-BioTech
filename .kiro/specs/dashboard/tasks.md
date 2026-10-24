# Dashboard (Lab Planner) — tasks

Build order from `frontend/BRIEF.md` section 12. P0 = must ship, P1 = before the 4:00 PM
freeze, P2 = after the freeze if the team agrees. Each task lists the requirement ids it
satisfies and its "done when". Run typecheck + tests after each task.

## P0 — core, nothing blocks on a backend change
- [ ] **P0-1** Scaffold (exact versions), tokens, fonts, two-column shell, start screen.
  _Requirements: R0, R1, R6._ Done when the start screen matches BRIEF section 4 at 1440 and 390 px.
- [ ] **P0-2** API client, capabilities, `normalize.ts`, zod schemas, banners, recorded-run
  loader, record-demo script. _R1, R14._ Done when a recorded run renders with the backend off.
- [ ] **P0-3** `<Num>` + provenance popover, dev guard and its test. _R15._ Done when the
  provenance test passes (every `[data-num]` has `[data-provenance]`).
- [ ] **P0-4** Topic block + matrix with weight sliders. _R4, R6._ Done when weights recompute
  instantly and the client total equals the server total within 1e-6.
- [ ] **P0-5** Design block: pair header, starting guess, ladder, plate map, facts. _R7._
  Done when the plate map shows the planned layout with hover details.
- [ ] **P0-6** Review thread with badges, red flags, rule checks. _R8._ Done when the
  unverified fixture shows the flag and reason, and model text never sits by a green badge.
- [ ] **P0-7** Robot check + uncertainty block (numbers, noise, calibration, next-changes list).
  _R9, R11._ Done when every number has provenance.
- [ ] **P0-8** Lab controls with what-if requests, live geometry, readout. _R12._ Done when the
  BRIEF 5.12 acceptance passes.
- [ ] **P0-9** Static bench deck with labware + mini plate. _R10._ Done when the deck renders
  with and without `sim.deck`.

## P1 — before the freeze
- [ ] **P1-1** Replay + plate audit (when steps are structured). _R10._ Done when replay runs
  at 16x and the audit lists the current compiler's issues.
- [ ] **P1-2** Run reveal choreography + reduced motion. _R2._ Done when it matches BRIEF 7.1.
- [ ] **P1-3** Try this change, pin, cost-against-certainty chart. _R13._ Done when two pins
  plot and the frontier draws.
- [ ] **P1-4** Pivot list (when neighbors exist), history, `?run=`, Share. _R5, R14._ Done when
  reload-by-link works.

## P2 — after the freeze, each behind its capability flag
- [ ] **P2** Async progress, fold-error dots, curve band, protocol viewer, model-card metrics,
  evidence drawer, skeptic turns, explored-topics matrix, pair picker.
  _R2, R4, R5, R7, R8, R9, R11._

## Property tests (BRIEF Appendix B, fast-check, `src/test/`)
B.1 matrix total · B.2 concentrations · B.5 Hill activity · B.7 planned layout ·
B.8 applyWhatIf limits · B.9 replay conservation · B.12 hashing. These double as the PBT
evidence for the Kiro write-up.

## Acceptance / demo script
BRIEF section 13 (13 checks). The Playwright MCP UI-review flow screenshots at 1440×900 and
390×844 and checks against the Banned list in `.kiro/steering/ui.md`.
