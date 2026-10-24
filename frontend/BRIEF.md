# Lab Planner dashboard: build brief for Kiro

Owner: frontend (C). Backend contact: Nghia (A). Written Sat 2026-10-24, 2:40 PM, against commit d2d4406, after reading every file in backend/, pipeline/orchestrator.py, database/ and mocks/, and running the compiler's protocol through the real Opentrons 10.1.0 simulator.

Kiro: read this whole file before writing code. Section 11 sets up the spec, steering, hooks and MCP from it. Section 12 is the build order. Where this brief and the code in backend/ disagree, the code wins. Tell the user what differed.

## How to start (paste into Kiro, in order)

The Kiro setup from section 11 is already on main (commit bb33ae7): steering file, three hooks, and the dashboard spec. Only `.kiro/settings/mcp.json` is missing, because Kiro blocks its own agent from writing MCP config. Create that file by hand with the JSON in 11.4.

1. On branch `new-branch-frontend`: "Merge origin/main into this branch. Read frontend/BRIEF.md completely, starting with 'Read first: build on the existing dashboard'. Update .kiro/specs/dashboard/tasks.md to the revised P0 in that section. Show me the diff of tasks.md."
2. "Execute the revised P0 tasks in order. After each task, run typecheck and tests. Stop after P0 and give me the URL to look at."
3. "Run the UI review flow from section 11.3 with the Playwright MCP, fix what it finds, then do P1."

## Read first: build on the existing dashboard (added 3:05 PM)

A teammate already built a working dashboard on branch `new-branch-frontend`: commits d0b0b45 ("Add React + Vite research dashboard (stage 5)") and d2844b5 ("extract hooks and split components"), React 18.3, Vite 5.4, TypeScript 5.6, about 4,200 lines. Build on it. Do not re-scaffold. This section overrides section 2, section 10 and tasks P0-1 to P0-9 wherever they disagree. Everything else in the brief applies to the existing code.

Setup on `new-branch-frontend`:
1. `git merge origin/main`. It should be conflict-free. Since the shared base (a86a5f0), main changed backend code, `.kiro/` and added `frontend/BRIEF.md`, while the branch changed only `frontend/` files that main never touched.
2. Keep React 18.3, Vite 5.4 and TypeScript 5.6. Do not upgrade during the hackathon.
3. Add only these packages (versions checked on npm on 2026-10-24, all accept React 18):

| Package | Version | Note |
|---|---|---|
| motion | 14.6.0 | import from `motion/react`, peer React 18 or 19 |
| @radix-ui/react-popover | 1.3.1 | |
| @radix-ui/react-slider | 1.6.1 | |
| @fontsource-variable/archivo | 5.3.0 | `wdth.css` |
| @fontsource-variable/newsreader | 5.3.0 | `opsz.css` |
| d3-scale, d3-shape, d3-array, d3-interpolate | 4.0.2, 3.2.0, 3.2.4, 3.0.1 | with @types/d3-scale 4.0.9, @types/d3-shape 3.2.0, @types/d3-array 3.2.2, @types/d3-interpolate 3.0.4 |
| vitest (dev) | 3.2.7 | not 5.x, which needs Vite 6.4 or newer. Run the `src/lib` tests in the Node environment, no jsdom needed |
| fast-check (dev) | 4.10.2 | property tests (Appendix B) |
| @playwright/test (dev) | 1.64.1 | e2e, including the provenance check in 5.15 |

Skip React Query, zustand and zod. The existing hooks (`useRun`, `useWhatIf`, `useReplay`, `useDataMode`) already hold the state. Add a `test` script (`vitest run`) and keep the existing `typecheck` script (`tsc --noEmit`). The provenance test from 5.15 runs in Playwright instead of vitest.

Where each brief section lands in the existing code:

| Brief | Existing file | Change |
|---|---|---|
| 5.1 top bar, question | TopBar.tsx, QueryForm.tsx | brand becomes Lab Planner, add server status, history, share, settings, examples, start screen |
| 5.2 progress, reveal | App.tsx, hooks/useRun.ts | stage strip and reveal |
| 5.4 topic | TopicPanel.tsx | |
| 5.6 matrix | ViabilityMatrix.tsx, sources.ts | fix A, contribution bar |
| 5.7 design | new components | |
| 5.8 review | SidePanels.tsx (`Evidence`) | becomes the review thread, fix C |
| 5.9 robot check | SidePanels.tsx (`RunCost`) | |
| 5.10 bench | RunReplay.tsx, hooks/useReplay.ts | deck drawing, fix B |
| 5.11 uncertainty | WhatIf.tsx shows the report today | own section in the notebook |
| 5.12 lab controls | WhatIf.tsx, hooks/useWhatIf.ts | move onto the bench, fix D |
| 5.15 provenance | Sourced.tsx, format.ts, sources.ts | `Sourced` is the brief's `<Num>`. Add the kinds and the link table |
| Appendix A types | types.ts | add the fields listed there |
| 3.4 client rules | api.ts, hooks/useDataMode.ts | add normalize.ts and capabilities.ts, fix E |

Fix these in the existing code first. Each one breaks a rule in section 0:
- A. `sources.ts` `axisProvenance` cites the OpenAlex topic (and the simulator) as the source of novelty, evidence, automatable and cost_time. The backend sets those four to constants today (0.55, 0.40, 1.0, 0.62), so the popover credits a source that did not produce them. Label them "Assumed value" until `matrix.axis_sources` arrives.
- B. `useReplay.ts` builds `demoSteps` from the design when the simulator sends fewer than 2 steps. Remove it and replay only real simulator steps. The real backend currently sends 142 steps that carry only a first-word action and no well, so the existing replay fills nothing. Disable Play with the 5.10 reason until steps carry `text` and `well` (backend item B0.4).
- C. `types.ts` `RationaleItem` has only `claim, pmid, verified`. The backend now also sends `evidence_type, evidence_id, quote, model_note, status, reason` (Appendix A). Badges come from `status`, `model_note` shows as "Model's note, not verified", and `chembl_activity` items link by `evidence_id` because their `pmid` is empty.
- D. `WhatIf.tsx` changes `dilution.factor` without touching `volumes_uL.diluent`. The backend's Monte Carlo uses the factor and the robot protocol uses the volumes, so they would simulate two different experiments. Apply B.8 (diluent = transfer x (factor - 1)) on every change.
- E. The app starts in mock mode, which shows `mocks/*.json`, and `mocks/README.md` calls those "placeholders, not results". Start in live mode, fall back to recorded runs (3.6), and keep mocks as a developer option labeled "Sample data from mocks/, not results".
- F. The default question "kinase inhibitors for liver fibrosis" matches none of the three prepared pairs. Start with an empty field and the three examples.
- G. Styling: replace the tokens at the top of `styles.css` with section 6. Drop IBM Plex Sans and IBM Plex Mono for Archivo and Newsreader. Remove the numbered middle-dot eyebrows ("01 · Topic viability", "03 · Protocol", "04 · Evidence"), monospace on numbers, and the identical 12 px white cards. All three are on the steering file's Banned list.

Revised P0 for this branch (replaces P0-1 to P0-9 in section 12, P1 and P2 stay as written):

| ID | Task | Done when |
|---|---|---|
| P0-1 | Merge main, add packages, swap tokens and fonts, fix F and G, two-column notebook and bench layout from section 4 | start screen and workspace match section 4 at 1440 and 390 px |
| P0-2 | normalize.ts, capabilities.ts, server status and banners, recorded runs and the record-demo script, fix E | a recorded run renders with the backend off |
| P0-3 | Extend `Sourced` to 5.15, fix A | the Playwright provenance check passes |
| P0-4 | Topic and matrix to 5.4 and 5.6 | weights recompute instantly and match the server total |
| P0-5 | Design block (5.7) | the plate map shows the planned layout |
| P0-6 | Review thread (5.8), fix C | the unverified fixture shows the flag and reason |
| P0-7 | Robot check (5.9) and the uncertainty section (5.11) | every number has provenance |
| P0-8 | Lab controls on the bench (5.12), fix D | the 5.12 acceptance passes |
| P0-9 | Bench deck (5.10), fix B | the deck renders, and Play is disabled with its reason until steps are structured |

At the 4:00 PM freeze, merge `new-branch-frontend` into main. The submission and the `hackachusetts-final` tag come from main.

## 0. Rules that override everything else

1. Every number on screen carries its source. Real numbers link to OpenAlex, PubMed, ChEMBL, a paper DOI, the Opentrons spec page or the Opentrons simulator. Numbers from our Monte Carlo say "Simulated, seed N, M runs". Numbers the dashboard computes list their inputs. A number without a source is a bug, and section 5.15 makes that testable.
2. Never invent data. No placeholder numbers, no fake progress percentages, no sample charts, no lorem ipsum. If the backend did not send something, say what is missing in one plain sentence.
3. The robot replay is a replay of the Opentrons simulator run. Say so on screen. No physical robot is involved.
4. Text written by a model is never shown as verified. Only the checker's `status` decides a badge.
5. No third-party logos anywhere (Opentrons, OpenAlex, ChEMBL, PubMed, Kiro). The Hackachusetts video rules forbid them. Draw the Flex deck as a schematic.
6. Work with the backend as it is today and light up features as the backend adds them (section 3.3). Never block a P0 task on a backend change.
7. Copy is sentence case, plain verbs, no exclamation marks, no em dashes, no "AI-powered".

## 1. What the user asked for, and where it lives

The product idea in the user's words: a researcher poses a research problem or topic. If it is too broad or already well explored, the tool shifts to a less known topic in the same field. A matrix with a score system shows how viable it is. Then lab automation: LLMs debate, do research, simulate the lab, and test the research and the lab. An interactive dashboard customizes lab settings and tries alternatives, with an area to watch the experiment being conducted in real time. Everything uses real data, a trained model scores topics, and an uncertainty model helps research save expense and time by exploring uncertain paths.

| User's words | Feature | Section | Backend data |
|---|---|---|---|
| Pose a research problem or topic | Question bar, start screen with examples | 5.1 | POST /api/run `query` |
| Too broad or well explored, shift to a less known topic in the same field | Crowding verdict, "Less explored topics nearby", one-click pivot | 5.4, 5.5 | `topic.counts_by_year`, `matrix.novelty`, `topic.neighbors` |
| A matrix with a score system for viability | Viability matrix with weight sliders, explored-topics matrix | 5.6, 5.5 | `topic.matrix` |
| LLMs debate, do research | Design review thread: designer proposal, checker verdict per citation, rule checks, skeptic turns once the backend adds them | 5.8 | `design.rationale`, `design.notes`, `design.review` |
| Simulate the lab, test the research and the lab | Robot check (Opentrons simulator verdict, cost, protocol) and the plate audit after replay | 5.9, 5.10 | `sim` |
| Customize lab settings, try alternatives | Lab controls (what-if), best next changes, pin and compare | 5.12, 5.13 | POST /api/uncertainty, POST /api/simulate |
| Watch the experiment in real time | The Bench: live Flex deck replaying the simulated run, stage-by-stage progress, simulated experiments landing in the uncertainty chart | 5.2, 5.10, 5.11 | `sim.steps`, run status, `uncertainty.samples` |
| Real data, not fabrication | Provenance popover on every number | 5.15 | `Source` on every field |
| Trained model scores the topic | Momentum with a model card | 5.4 | `topic.momentum` |
| Uncertainty model saves expense and time | Fold-error results, changes ranked by error drop per cost, cost against certainty chart | 5.11, 5.13 | `uncertainty`, `next_experiments` |

Product name in the UI: "Lab Planner" (the team's working name). Keep it in one constant, `APP_NAME`.

## 2. Stack and setup

Versions checked on npm on 2026-10-24. Pin exact versions.

| Package | Version | Use |
|---|---|---|
| create-vite, template react-ts | 9.3.1 | scaffold into frontend/ (keep the existing README.md, merge its backend notes into the new one) |
| vite | 8.3.5 | dev server and build |
| react, react-dom | 19.3.1 | UI |
| typescript | the template's ~6.0.3 | do not upgrade to 7.0.2 |
| @vitejs/plugin-react | 6.1.2 | |
| motion | 14.6.0 | animation, import from `motion/react` |
| @tanstack/react-query | 5.104.5 | server state |
| zustand | 5.0.16 | UI state |
| zod | 4.6.7 | validate API responses at the boundary |
| d3-scale 4.0.2, d3-shape 3.2.0, d3-array 3.2.4, d3-interpolate 3.0.1 | | hand-built SVG charts |
| @radix-ui/react-popover | 1.3.1 | provenance popover |
| @radix-ui/react-slider | 1.6.1 | weight and lab-control sliders |
| @fontsource-variable/archivo | 5.3.0 | `import "@fontsource-variable/archivo/wdth.css"`, family `'Archivo Variable'`, width 62% to 125%, weight 100 to 900 |
| @fontsource-variable/newsreader | 5.3.0 | `import "@fontsource-variable/newsreader/opsz.css"`, family `'Newsreader Variable'`, weight 200 to 800 |
| openapi-typescript (dev) | 7.13.0 | types from /openapi.json |
| vitest, @testing-library/react, fast-check (dev) | 5.0.5, 16.3.3, 4.10.2 | unit and property tests |
| @playwright/test (dev) | 1.64.1 | e2e smoke and screenshots |

No Tailwind, no shadcn, no component kit, no chart library, no icon pack. CSS Modules plus CSS custom properties.

Config:
- `vite.config.ts`: dev proxy `/api` and `/openapi.json` to `http://127.0.0.1:8000`.
- `.env.example`: `VITE_API_BASE=` (empty means same origin through the proxy. Set it to the deployed backend URL for production builds.)
- `.gitignore`: `node_modules`, `dist`, `.env.local`. Commit `frontend/screenshots/`, the Kiro write-up uses it.

npm scripts: `dev`, `build`, `preview`, `typecheck` (`tsc -b --noEmit` or the template's equivalent), `test` (`vitest run`), `e2e` (`playwright test`), `gen:api` (`openapi-typescript http://127.0.0.1:8000/openapi.json -o src/api/schema.d.ts`), `record:demo` (`node scripts/record-demo.mjs`).

Backend for local work:

```
pip install -e ".[dev]"
pip install -e ".[robot]"          # real Opentrons simulator, needs Python 3.13 or lower
python scripts/init_db.py
uvicorn backend.api:app --reload   # http://127.0.0.1:8000, docs at /docs
```

## 3. Backend connection

### 3.1 Endpoints today (commit d2d4406)

| Method and path | Request | Response | Time |
|---|---|---|---|
| GET /api/health | none | `{"status": "ok"}` | instant |
| POST /api/run | `{query: string (min 1), weights?: {momentum, novelty, evidence, automatable, cost_time}, runs?: 1-5000 (1000), seed?: int (42), reader_cv?: 0-0.5 (0.05)}` | `{run_id, blocked, topic, design or null, sim or null, uncertainty or null}` | a few seconds, longer on the first call (the server imports the Opentrons package) |
| GET /api/run/{run_id} | none | `{run_id, meta: {run_id, query, created_at, status}, topic, design, sim, uncertainty}`, any report can be null | instant |
| POST /api/uncertainty | `{design: ExperimentDesign, runs?, seed?, reader_cv?}` | UncertaintyReport with `next_experiments` | about 1 to 2 s (1,000 curve fits plus 3 or 4 planner reruns) |

Quirks the client must absorb, all inside `src/api/normalize.ts` and nowhere else:
- POST /api/run returns `safety.pass` and `simulator.pass`. GET /api/run/{run_id} returns stored JSON with `passed`. Read both into `ok: boolean`.
- Responses are untyped in OpenAPI today, so hand-write the types (Appendix A) until `RunResponse` appears in /openapi.json.
- The design always uses the first demo pair, lapatinib on HER2, whatever the question. Show the pair and the notice in 5.7.
- Stage 1 falls back to invented counts when OpenAlex is unreachable, and they are labeled `openalex` today. Detect them by `topic.topic.openalex_id === "T00000"` (or `topic.offline` once the backend sends it) and do not draw them.
- Matrix axes other than momentum are constants today (novelty 0.55, evidence 0.40, automatable 1.0, cost_time 0.62). Without `matrix.axis_sources`, label those four "Assumed value".
- `neighbors` holds one placeholder today (`openalex_id "T00001"`, name "placeholder neighbor"). Drop any neighbor with that id or a name starting with "placeholder".
- `sim.steps` carries only a lowercased first word today ("picking", "aspirating") with no well or volume. Treat steps without `text` as not replayable.
- `sim.cost` is a formula today, not counted from the simulator. Without `cost.source`, label it "Estimated by formula".
- `rationale` items of type `chembl_activity` have an empty `pmid`. Link them by `evidence_id` (a ChEMBL activity id).
- `next_experiments` carry only a text label. The planner produces four labels today: `add 1 replicate (N total)`, `add 2 dilution points`, `tighten dilution factor to X`, `raise transfer volume to 5 µL`. Parse them (Appendix B.11) until `next_experiments[i].design` arrives.

### 3.2 What the backend is adding

The backend owner has a matching list in backend/DASHBOARD_GAPS.md (B0 first, then B1, B2 only if time). Field names below match it exactly.

### 3.3 Capability detection

At boot, GET /openapi.json once and derive flags. Also check optional fields on each response. Every feature has a fallback and none of them blocks P0.

| Capability | Detect | Unlocks | Fallback |
|---|---|---|---|
| Typed responses (B0.1) | `components.schemas.RunResponse` | `npm run gen:api` types | hand-written types |
| Pair choice (B0.3) | path `/api/pairs`, RunRequest property `compound_chembl_id`, response `pair` | pair picker, design matches the question | show the pair used plus the notice |
| Structured steps (B0.4) | `sim.steps[0].text` present | replay, plate audit | replay button disabled with the reason |
| Deck map (B0.4) | `sim.deck` non-empty | deck from data | fixed layout in 5.10 |
| Cost from the run log (B0.5) | `sim.cost.source` | "Counted from the simulator run log" | "Estimated by formula" |
| What-if robot check (B0.6) | path `/api/simulate` | cost and replay follow the sliders | cost shows the run's numbers, labeled "for the original design" |
| Honest topic (B0.2) | `topic.offline`, `matrix.axis_sources` | per-axis provenance | rules in 3.1 |
| Per-field noise sources (B0.8) | `noise.field_sources` | exact source per noise row | the block's `sources` list |
| Plan flag (B0.9) | WhatIfRequest property `plan` | fast previews while dragging | request only on release |
| Planner designs (B1.2) | `next_experiments[0].design` | exact "Try this change", before and after p90 | label parser |
| Samples (B1.3) | `uncertainty.samples` | fold-error dot chart | numbers only |
| Curve band (B1.3) | `uncertainty.curve` | dose-response band | expected curve from the prior, labeled |
| Protocol text (B1.4) | path `/api/protocol/{name}` | protocol viewer | show the file path |
| Source URLs (B1.6) | `source.url` | direct links | link builder table in 5.15 |
| Async run (B2.1) | RunRequest property `mode` | live stage progress | one request, staged reveal |
| Neighbors (B2.2) | non-placeholder `topic.neighbors` | pivot list | section hidden |
| Metrics (B2.3) | path `/api/metrics` | model card numbers | model tag only |
| Evidence (B2.4) | path `/api/evidence/{compound_chembl_id}` | abstract drawer with highlighted quotes | PubMed links only |
| Skeptic (B2.5) | `design.review` non-empty | skeptic turns in the review | thread without them |

### 3.4 Client rules

- One fetch wrapper in `src/api/client.ts`. Base URL is `import.meta.env.VITE_API_BASE` or `""`.
- AbortController timeouts: run 90 s, uncertainty 30 s, simulate 15 s, everything else 10 s.
- What-if: cancel the in-flight request when a new one starts, and drop any response whose `design_id` is not the current draft's.
- React Query: query keys include a stable hash of the request body (Appendix B.12). POST run uses `retry: 0`, GETs `retry: 1`.
- Validate responses with zod at the boundary. Objects are loose (unknown keys pass, zod 4 strips them by default which is fine). On failure, show a developer panel naming the failing path (example: "topic.matrix.total is missing") with "Show raw response".
- Errors: network failure (banner, 5.1), 422 (show FastAPI's `detail[i].msg` next to the control named by `detail[i].loc`), 404 run id ("This run doesn't exist on this server"), 500 (show `detail` and "Try again").
- Cold start: if GET /api/health has not answered in 4 s, show "The server is waking up. Free hosting can take up to a minute." with "Open a recorded run" beside it.
- What-if designs get a new `design_id`: `${original}-w${hash6}` (letters, digits and dashes only), so the backend never overwrites the run's protocol file.
- Never send a design the backend will reject. Enforce the 5.12 limits in the browser.

### 3.5 Types

Until `RunResponse` exists in OpenAPI, `src/api/types.ts` mirrors backend/contracts by hand (Appendix A). Then run `npm run gen:api` and switch imports to `src/api/schema.d.ts`. `normalize.ts` stays the only file that knows about backend quirks.

### 3.6 Recorded runs

`public/demo/` holds raw RunResponse JSON captured from the real backend, never edited by hand, plus `index.json` as `[{file, question, recorded_at, commit}]`. `scripts/record-demo.mjs` posts the three example questions to the running backend and saves the responses. Re-record after each backend milestone. When a recorded run is open, show "Recorded run from {date}" in the top bar. Lab controls still call the server when it is up.

## 4. Layout

Concept: the bench. The page is a lab bench (cool grey-green). The notebook is one sheet of paper on it, holding the stages in order. The Flex deck is the one instrument, always in view. Color is reserved for meaning: the plate's activity ramp and the verification statuses. Everything else is ink on paper. All text is left aligned.

Desktop, 1200 px and wider: two columns. Left, the notebook: one scrolling sheet, prose capped at 68ch, stages in order with a large stage numeral in the left margin (the stages are a real sequence). Right, the Bench: 480 px, sticky under the top bar, holding the deck, replay controls, lab controls and the live readout. From 900 to 1199 px the bench is 400 px. Below 900 px everything is one column, the bench becomes a section right after Design, and lab controls open in a bottom sheet from a fixed "Adjust lab settings" button.

Start screen:

```
+----------------------------------------------------------------------------------+
| Lab Planner                                               History    o Connected |
+---------------------------------------------+------------------------------------+
|                                             |                                    |
|  What do you want to test?                  |   +--------+--------+--------+     |
|  +---------------------------------------+  |   | A1     | A2     | A3 bin |     |
|  | HER2 kinase inhibitors in breast c... |  |   +--------+--------+--------+     |
|  +---------------------------------------+  |   | B1     | B2     | B3     |     |
|  [ Run ]   Advanced settings                |   +--------+--------+--------+     |
|                                             |   | C1     | C2     | C3     |     |
|  Try one                                    |   +--------+--------+--------+     |
|  HER2 kinase inhibitors in breast cancer    |   | D1     | D2     | D3     |     |
|  p38 MAPK inhibitors in inflammation        |   +--------+--------+--------+     |
|  JAK inhibitors in autoimmune disease       |   Your experiment will be laid     |
|                                             |   out here.                        |
|  1 Checks how crowded the topic is          |                                    |
|  2 Designs a first experiment, checks       |                                    |
|    every citation                           |                                    |
|  3 Runs it in the Opentrons simulator       |                                    |
|  4 Simulates real-world noise               |                                    |
+---------------------------------------------+------------------------------------+
```

Workspace:

```
+----------------------------------------------------------------------------------+
| Lab Planner  [ HER2 kinase inhibitors in breast cancer      ] [Run]  Share  Hist. |
| 1 Topic  done    2 Design  done    3 Robot check  done    4 Uncertainty  done     |
+---------------------------------------------+------------------------------------+
| NOTEBOOK (scrolls)                          | BENCH (sticky)                     |
|                                             |  Flex deck, labware in D1 D2 D3,   |
| 1  Topic name, link to OpenAlex             |  trash in A3, pipette head         |
|    Counts 2015-2024 chart    Momentum 71%   |  [Play] 1x 4x 16x  Step 37 of 114  |
|    Crowding verdict, nearby topics          |  Aspirating 50.0 uL from A1 of ... |
|    Viability matrix with weights            |  --------------------------------  |
|                                             |  Lab controls                      |
| 2  Lapatinib on HER2                        |   Top concentration   2,399 nM     |
|    Starting guess, dilution ladder          |   Dilution factor     3            |
|    Plate map 8 x 12, facts                  |   Concentrations      10           |
|    Design review thread                     |   Replicates          3            |
|                                             |   Transfer volume     50 uL        |
| 3  Passed the Opentrons simulator           |  --------------------------------  |
|    Cost, run log, protocol                  |  p90 1.31x   median 1.08x          |
|                                             |  tips 11     compound 50 uL        |
| 4  Simulated, seed 42, 1,000 runs           |  [Pin for comparison]  A  B        |
|    Headline, distribution, noise,           |                                    |
|    calibration, best next changes,          |                                    |
|    cost against certainty                   |                                    |
+---------------------------------------------+------------------------------------+
```

Mobile, 390 px:

```
+------------------------------+
| Lab Planner        History   |
| [question.................]  |
| [Run]                        |
| 1  2  3  4   (stage strip)   |
| Notebook sections stacked    |
| Bench after section 2,       |
| deck at full width           |
| [Adjust lab settings] fixed  |
|  -> bottom sheet controls    |
+------------------------------+
```

## 5. Feature specs

Each part lists data, behavior, states, provenance and motion. "Acceptance" lines are what the e2e test and the demo script check.

### 5.1 Top bar, question and settings

- Product name, the question field (stays editable after the first run), Run, Share, History, and a server status with text, not color alone: "Connected", "Can't reach server", "Waking up".
- Enter runs. While running, the button reads "Running" and is disabled.
- Advanced settings (a disclosure under the field): "Simulated experiments" (`runs`, 100-5000, default 1000), "Random seed" (`seed`, default 42), "Plate reader scatter" (`reader_cv`, 0-50%, default 5%). They go into POST /api/run and every what-if request.
- Start screen: label "What do you want to test?", helper text from section 8, three example questions that fill the field and run, and the 4-step "How it works" list.
- Server down: banner "Can't reach the Lab Planner server at {base}. Start it with `uvicorn backend.api:app --reload`, or open a recorded run." with a list of recorded runs.
- Acceptance: example click runs. Killing the backend shows the banner within 10 s, and a recorded run opens.

### 5.2 Run progress and the reveal

- Stage strip under the top bar: "1 Topic", "2 Design", "3 Robot check", "4 Uncertainty". States: waiting, running, done, blocked, failed. Each state has text and a shape, not just a color. Clicking a stage scrolls the notebook to it.
- Today's synchronous backend: after Run, all four stages read "running" and one honest line appears: "Running all four stages. Usually a few seconds, longer on the first run of the day." No percentages, no fake stepping. When the response lands, reveal the stages in order, 350 ms apart, synchronized with the bench (7.1).
- Async backend (B2.1): POST returns `run_id`, poll GET /api/run/{run_id} every 500 ms, reveal each stage when its report appears, stop at status `done` or `error`.
- A failed stage shows its error and keeps earlier stages visible.
- Acceptance: no number appears before the data for it arrives. A slow response never shows fake progress.

### 5.3 Safety gate

- When `blocked` is true or the safety gate did not pass, the notebook shows only the blocked panel. Title: "Lab Planner doesn't design experiments for this topic." Then `safety.reasons` verbatim as a list (for example "blocked term: 'gain of function'"). Then "It designs in-vitro dose-response experiments for benign targets." Button "Ask a different question" focuses the field. The bench stays empty. No matrix, no neighbors.
- Acceptance: "gain of function influenza" shows the blocked panel with the reason.

### 5.4 Topic

Data: `topic.topic {openalex_id, name}`, `counts_by_year [{year, works, source}]`, `momentum {p_growth, model}`.

- Header: the topic name with "Topic in OpenAlex" as its source link.
- Yearly counts: vertical bars for each year sent (2015-2024), hand-built SVG. Bars in graphite, the last five years (the crowding window) in ink. Y axis "Works per year" with 3 ticks. Hover or focus a bar for its provenance: "2019: 812 works. OpenAlex topic T10966, works grouped by publication year", linked. Screen readers get a visually hidden table.
- Momentum: a horizontal 0-100% scale with a marker at `p_growth` and a tick at 50%. Sentence: "71% chance this topic grows faster than the typical topic over the next five years." The model card popover gives the model tag (for example hgb-v3) and "Trained on OpenAlex topics, using 2015-2019 publication counts to predict 2020-2024 growth", plus AUROC and the baseline from /api/metrics when present. Model `slope-heuristic`: "Rough estimate from the publication trend. The trained model wasn't available." Model `offline-placeholder`: hide momentum.
- Crowding verdict, only when novelty has a real (not assumed) source: novelty below 0.33 "Crowded topic", 0.33 to 0.66 "Moderately explored", above 0.66 "Open topic", followed by the 2020-2024 works total. The popover states the bands.
- Offline counts: no chart. "OpenAlex couldn't be reached, so topic numbers aren't shown. The experiment below doesn't depend on them."
- Motion: bars grow from the baseline left to right during the reveal only.

### 5.5 Less explored topics and the explored-topics matrix

- "Less explored topics nearby": shown only when real neighbors exist. Each row: name, works in the last 5 years (source), momentum, a comparison to the current topic ("1/15 as many papers"), button "Explore this topic". When the verdict is "Crowded topic", place this list directly under the verdict. This is the user's "shift to a less known topic".
- "Explore this topic" moves the row's name into the question field (shared layout animation), sends `openalex_topic_id` when the backend accepts it, and runs.
- Explored-topics matrix (P2): rows are topics from this browser's run history, columns Momentum, Novelty, Evidence, Automatable, Cost and time, Viability. Viability is recomputed with the current weights, so the rows re-rank live when weights change. Click a row to reopen its run. Stored in localStorage inside try/catch, at most 20 rows.

### 5.6 Viability matrix

Data: `matrix {momentum, novelty, evidence, automatable, cost_time, weights, total}`, plus `axis_sources` and `axis_notes` when present.

- Title "How viable is this topic?". A table with one row per axis: name with a one-line meaning, value bar from 0 to 1 with the number, weight slider (0-100, step 5), and contribution (axis x weight / sum of weights).
- Axis meanings: Momentum "How likely the field is to grow." Novelty "How uncrowded the topic is." Evidence "How much published data gives a starting point." Automatable "Whether a robot can run the first experiment." Cost and time "How cheap and quick the first experiment is."
- Total: large number with the label "Viability", above a contribution bar of five segments that sum to the total. Segments alternate ink and graphite tones with 2 px gaps. An axis with assumed provenance draws as a dotted outline instead of a fill. Hovering a segment highlights its row.
- Sliders recompute instantly in the browser with Appendix B.1. Each slider shows its effective share ("20%"). "Reset weights" restores 0.2 each. The current weights go with the next Run.
- Provenance per value: `axis_sources[axis]` when present. Without it, momentum points to the model and the other four read "Assumed value. Not computed from this topic's data."
- All weights at zero: the total reads "No weights set" and the bar empties.
- Motion: segment widths spring when weights change, the total tweens.
- Acceptance: dragging Momentum to 0 changes the total immediately. With default weights the client total equals the backend total within 1e-6.

### 5.7 Experiment design

Data: `design {design_id, topic_id, assay {type, readout, target_chembl_id, compound_chembl_id}, prior_ic50 {median_nM, n_measurements, spread_log10, source}, dilution {top_nM, factor, points}, replicates, controls {positive_wells, negative_wells}, plate {labware, layout}, volumes_uL {transfer, diluent}, pipette, tiprack, rationale, notes}`, plus `pair` when sent.

- Header: "{Compound} on {target}", for example "Lapatinib on HER2", with ChEMBL links for both ids. Names come from `pair`, else from this fallback map: CHEMBL554 lapatinib, CHEMBL1824 HER2, CHEMBL10 SB-203580, CHEMBL260 p38alpha (MAPK14), CHEMBL221959 tofacitinib, CHEMBL2971 JAK2. If `pair.match` is "default", or there is no `pair` and the question names neither the compound nor the target, show: "Your question didn't match a prepared compound and target, so this design uses lapatinib on HER2 as a worked example."
- Pair picker (when /api/pairs exists): a small select "Compound and target" listing the three pairs. Changing it reruns with `compound_chembl_id`.
- IC50, explained once: "IC50 is the concentration that cuts the target's activity in half. Lower means more potent."
- Starting guess: "Starting guess: 24.0 nM, the median of 21 published measurements in ChEMBL. Labs disagree by about 8.6-fold (one standard deviation)." 8.6 = 10^`spread_log10`, shown as a formula in its popover. The prior source id is a comma-separated list of up to 10 ChEMBL activity ids. Link each one.
- Dilution ladder (SVG, horizontal log10 axis in nM): one dot per concentration (Appendix B.2), the starting guess as a vertical line, a light band of plus or minus max(2, 1.645 x spread) log units (the designer's target range, B.4) and a darker band of plus or minus one lab-to-lab standard deviation. Caption: "10 concentrations from 2,399 nM down to 0.12 nM, each one third of the one before."
- Plate map (96 wells, rows A-H, columns 1-12, labels in condensed Archivo): the planned layout from Appendix B.7. Each well's fill is the expected activity at the starting guess on the activity ramp (B.5, B.6). Hover or focus a well: "B4: 88.9 nM, replicate 2. Expected 21% activity at the starting guess (Hill slope 1 assumed)." Legend: the ramp from 0% to 100% activity, plus marks for negative and positive controls. Label: "Planned layout". After a replay, a toggle "Planned" or "After robot run" shows the replayed final state, and the plate audit (5.10) lists differences.
- Facts: replicates, controls (positive, negative), wells used ("38 of 96", computed), transfer and diluent volumes, pipette, tip rack, plate. Display names from `src/lib/labware.ts`: `flex_1channel_1000` "Flex 1-Channel 1000 µL", `flex_1channel_50` "Flex 1-Channel 50 µL", `opentrons_flex_96_tiprack_200ul` "Flex 96 tip rack, 200 µL", `corning_96_wellplate_360ul_flat` "Corning 96-well plate, 360 µL, flat", `nest_12_reservoir_15ml` "NEST 12-well reservoir, 15 mL".
- `design.notes` render as plain sentences under the facts.

### 5.8 Design review (the debate)

- Title "Design review". Summary line: "5 of 5 evidence items verified" (count of `status === "verified"` over the total). If any item is not verified, a red line above the thread: "2 items could not be verified", each a jump link.
- The thread, in order:
  1. Designer turn, rendered by code from the design and never from model text: "Proposed 10 concentrations at a 3-fold dilution from 2,399 nM to 0.12 nM, 3 replicates, 4 positive and 4 negative controls, starting from the median of 21 ChEMBL measurements."
  2. One turn per rationale item, attributed to "Citation checker":
     - `chembl_activity`: the claim text (the checker re-renders it from the record, so it is code text), the badge, and a link "ChEMBL activity 190222".
     - `abstract_quote`: the quote set in Newsreader with a PMID link to `https://pubmed.ncbi.nlm.nih.gov/{pmid}/`, plus title, journal and year when evidence is available. The badge reads "Verified quote" only when `status` is verified. `model_note` sits below in graphite, labeled "Model's note, not verified".
     - `partial`: amber badge "Partly verified" and the `reason`.
     - `unverified`: red flag "Not verified" and the `reason` in full.
  3. Rule checks, computed in the browser from the design and labeled "Rule checks": "Covers the starting guess: 2.0 log units above and 2.3 below (target 2.0)" (B.3, B.4), "Transfers stay at or above 5 µL, the 1000 µL pipette's minimum", "Fits on one plate: 38 of 96 wells", "Dilution factor matches the volumes: (50 + 100) / 50 = 3". Each passes or fails with a shape and text.
  4. Skeptic turns, when `design.review` exists: the argument labeled "Model's argument, not verified", the proposed change, what the simulation said (p90 before and after, extra tips), and the verdict "Simulation supports this change" or "Simulation doesn't support this change", with "Try this change".
- Badges are an icon plus text in the status color, no pill backgrounds: check in a circle for verified, half-filled circle for partly verified, flag for not verified.
- Acceptance: a fixture with one unverified item shows the red line, the flag and the reason. Model text never appears next to a green badge without its "not verified" label.

### 5.9 Robot check

- Verdict. Passed: "Passed the Opentrons simulator", with "{seconds} s, {log_lines} log lines, Opentrons {opentrons_version}" as simulator-sourced numbers. If `opentrons_version` contains "not installed": amber "Static check only. The Opentrons package isn't installed on the server, so the protocol wasn't simulated." Failed: red, `simulator.error` verbatim in a readable block, then "The protocol comes from a fixed template, so this is a backend bug to report, not something to edit by hand."
- Cost: tips, compound µL, plates, robot steps, each with provenance. With `cost.source`: "Counted from the simulator run log". Without it: "Estimated by formula, not counted from the simulator".
- Run log: collapsible list of steps (`text` when present, else `action`). The current replay step is highlighted and scrolled into view.
- Protocol: "View protocol" opens a panel with the Python file when `/api/protocol/{name}` exists (name = basename of `protocol_file` without `.py`). Otherwise show the path. Caption: "Generated from a fixed template. No model-written code runs."

### 5.10 The Bench and the replay (the signature element)

This is the one element that carries the product's personality. Everything around it stays quiet.

Drawing (SVG, real SBS geometry so it reads as a real deck):
- Deck: 4 rows, A at the top of the drawing (back of the robot) to D at the bottom, and 3 columns 1-3 left to right. Slot 127.76 x 85.48 mm. Scale to the bench width. Deck base in `--deck` with a 1 px light top-left edge and a 1 px darker bottom-right edge, like machined aluminum. Slot recesses in `--slot`, slot labels ("D1") in condensed Archivo at each slot's top-left.
- Labware: from `sim.deck` when present, else the fixed compiler layout: D1 tip rack, D2 96-well plate, D3 12-well reservoir (A1 diluent, A2 compound), A3 trash bin. Empty slots show only their label.
- Wells and tips: 8 x 12, A1 center at 14.38 mm from the left and 11.24 mm from the top of the slot, 9 mm pitch. Tips present are filled graphite circles. Used tips are dashed empty rings. Plate wells are empty rings until liquid arrives, then fill with the activity color, opacity by volume.
- Reservoir: 12 tall troughs at the same 9 mm pitch. A1 labeled "Diluent", A2 "Compound". The fill level drops as liquid leaves.
- Trash: an outlined bin with a tip count.
- Pipette head: a 2 px ink ring with a short stem, a gantry line across the deck at the head's height, a small tip shape under it while a tip is loaded, and a liquid fill in the tip colored by what it carries.

States:
- Idle (no run): empty deck, slot labels, "Your experiment will be laid out here."
- After design: labware drops into slots, the plate shows the planned layout.
- Replay (needs structured steps): Play and Pause, speed 1x, 4x, 16x, "Skip to end", a scrubber over leaf steps, "Step 37 of 114" (today's lapatinib protocol has 142 log entries, 114 of them leaf actions), and the current log line verbatim under the deck. Caption: "Replay of the Opentrons simulator run. No physical robot was used." Without structured steps the Play button is disabled with "Replay needs step details from the server (backend item B0.4)."

Replay behavior (state machine in `src/lib/replay.ts`, pure and unit-tested, Appendix B.9):
- Leaf actions animate: `pick_up_tip` (head travels to the tip, the tip leaves the rack), `aspirate` (head to source, source level drops, tip fills with that liquid's color), `dispense` (head to target, the well fills and recolors by its computed concentration), `mix` (the well pulses 3 times quickly), `drop_tip` (head to the trash, count goes up), `blow_out` (empties the tip into the location).
- Group headers (`transfer`, and `mix` when it has children) show as a caption above the current line: "Transferring 50 µL from A1 to A2".
- Reservoir A2 starts as compound stock at `dilution.top_nM`. Reservoir A1 is diluent at 0 nM. Wells recolor by expected activity at the starting guess for their computed concentration, so the row turns from blue (high concentration, target shut down) to pink (low concentration, target active) as the dilution proceeds.
- Plate audit at the end (the "test the lab" moment): compare the final state with the plan (B.7) and list differences in plain words. The current compiler should produce exactly these: "A1 ends empty, so the top concentration can't be read", "A10 ends with 150 µL instead of 100 µL", "Rows B and C are never filled, so the design's 3 replicates aren't run", "Controls in column 12 are never filled". Show the audit prominently when it finds problems. When there are none: "Every well ends as planned."
- Timing at 1x: 350 ms travel, 250 ms action. At 16x the 114 leaf steps finish in about 4 s.
- The mini plate in D2 mirrors the large plate map.
- Keyboard: Space toggles play while the bench has focus, Left and Right arrows step.
- Reduced motion: no head travel. Each tick applies its step instantly and updates the log line.

### 5.11 Uncertainty

Data: `uncertainty {design_id, label, runs, seed, noise {lab_spread_log10, pipette_cv, pipette_bias, reader_cv, sources}, fold_error {median, p90}, outside_range_share, failed_fit_share, calibration {coverage_90, pairs}, next_experiments}`, plus `samples` and `curve` when present.

- The whole section sits in a simulated block: a hatched strip on its left edge and the label "Simulated, seed 42, 1,000 runs". Inside it, only the noise levels and the calibration carry real sources.
- Headline: the p90 fold error as the large number ("1.31x" in these examples), and the sentence "In 9 of 10 simulated experiments, the measured IC50 lands within 1.31x of the true value. Half land within 1.08x." (p90 and median, always from the server.)
- Fold-error dots (with `samples`): a dot histogram on a log x axis from 1x upward, one dot per simulated experiment, median and p90 lines labeled. During the reveal the dots drop in quickly, which is the "experiments being run" moment. Without samples, the two numbers only.
- Dose-response band (with `curve`): log concentration on x, % activity on y, a p10 to p90 band, a p50 line, the expected curve from the starting guess dashed, and the dilution concentrations as ticks. Without `curve`, the expected curve alone, labeled "Expected from the starting guess".
- Risks: "In 3% of simulated runs the true IC50 fell outside the tested range." Above 5%, add "Widen the range", which raises the top concentration by one dilution step in the lab controls. "0% of curve fits failed."
- Noise model table, one row each: lab-to-lab spread ("0.932 log units, about 8.6-fold"), pipetting scatter (CV %), pipetting bias (%), plate reader scatter (% of signal, user setting). Source column from `noise.field_sources`, else the block's `sources` (the Kalliokoski 2013 paper DOI and the Opentrons Flex pipette spec). One line under it: "Biology dominates. Labs disagree far more than the robot errs."
- Calibration: "Checked against real data: the 90% range contained 89% of 412 held-out ChEMBL measurements. The target is 90%." Draw coverage against the 90% mark on a short bar. (Use the numbers the server sends, these are examples.)

### 5.12 Lab controls (what-if)

On the bench, under the deck. Each slider shows its label, value, unit, and the designed value as a small tick on the track. "Reset to designed values" restores everything.

| Control | Field | Range | Step | Note under the control when relevant |
|---|---|---|---|---|
| Top concentration | `dilution.top_nM` | 1 to 100,000 nM, log scale | 0.05 decade | the designer caps at 100,000 nM |
| Dilution factor | `dilution.factor` | 2 to 10 | 0.5 | diluent follows (B.8) |
| Concentrations | `dilution.points` | 4 to 11 | 1 | column 12 holds controls |
| Replicates | `replicates` | 1 to 8 | 1 | one plate row each |
| Transfer volume | `volumes_uL.transfer` | 5 to 100 µL | 1 | 5 µL is the 1000 µL pipette's minimum (Opentrons spec) |
| Plate reader scatter | request `reader_cv` | 0 to 50% | 1% | |
| Simulated experiments | request `runs` | 100 to 5,000 | 100 | |

Coupling and limits live in `applyWhatIf` (Appendix B.8). It returns the new design plus plain notes, for example "Transfer lowered to 30 µL so the top well stays under 300 µL."

Flow:
- While dragging: geometry updates every frame (dilution ladder, plate map, mini plate, rule checks, wells used). Numbers that need the server dim to 50% with a thin progress line under the readout. No spinners.
- When the backend accepts `plan`, send a preview with `plan: false` 250 ms after the last movement.
- On release (Radix `onValueCommit`): POST /api/uncertainty with `plan: true`, and POST /api/simulate when available, both with the patched design and a new `design_id`. Cancel older requests. When results land, numbers tween from old to new and an outlined ghost of the previous p90 stays for 1.5 s.
- Live readout under the controls: p90 fold error, median, outside-range share, tips, compound µL, wells used, each with provenance.
- Acceptance: changing Concentrations from 10 to 8 updates the plate map at once, and the fold error updates about 2 s after release with the old value ghosted.

### 5.13 Best next changes, pin and compare

- "Best next changes": `next_experiments` in the order sent (the server ranks by score). Each row: the change in sentence case, the improvement, the extra cost ("+6 tips", "+0 µL compound", "+0 plates"), and "Try this change".
  - Improvement with `p90_after`: "p90 fold error 1.31x to 1.25x". Without it: "18% less excess error", where the popover explains: "Measured on the part of the fold error above 1x: (p90 before - p90 after) / (p90 before - 1)."
  - Score in the popover: "Error drop in percent per cost unit. 1 tip, 10 µL of compound, or 1/50 of a plate each count as 1 unit."
- "Try this change" applies `next.design` when present, else the parsed label (B.11), to the lab controls, then recomputes. If the change breaks a limit, the button is disabled with the reason, for example "Needs 12 concentrations, and the plate fits 11 beside the control column."
- "Pin for comparison" saves `{letter A-D, design, cost, fold_error}`, at most 4, keyed by compound. Pins show as letter chips under the readout. Click loads, x removes.
- "Cost against certainty" chart: x is tips (toggle to compound µL), y is p90 fold error, lower is better. Points: the current design (filled ink), pins (letters), planner suggestions (outlined, at current tips + extra tips and `p90_after`, omitted without `p90_after`). A line joins the non-dominated points. Hover shows provenance. Click loads the design.

### 5.14 History and sharing

- `?run={run_id}` loads GET /api/run/{run_id}. `?demo={file}` loads a recorded run.
- History drawer: runs from this browser (localStorage, inside try/catch): question, topic name, viability, p90, time ago. Click reopens.
- Share copies the `?run=` link and confirms with "Link copied".

### 5.15 Provenance (the trust feature)

- `<Num value format provenance />` renders the formatted number with a 1 px dotted graphite underline. Hover for 300 ms, focus, or click opens a Radix Popover. Esc closes. Tap opens on touch.
- The popover shows the kind, the id, a link when one exists, and a "How this is computed" line for derived values.
- Kinds and labels: `openalex` "OpenAlex", `pubmed` "PubMed", `chembl_activity` "ChEMBL activity", `semantic_scholar` "Semantic Scholar", `paper` "Paper", `spec` "Opentrons spec", `simulator` "Opentrons simulator", `simulated` "Simulated (seed N, M runs)", `assumed` "Assumed value", `derived` "Computed here from" plus the inputs, each with its own source.
- Links: `source.url` when present. Otherwise build them in `src/lib/provenance.ts`:

| Kind | Link |
|---|---|
| OpenAlex counts | `https://api.openalex.org/works?filter=topics.id:{id},from_publication_date:2015-01-01,to_publication_date:2024-12-31&group_by=publication_year` |
| OpenAlex topic | `https://api.openalex.org/topics/{id}` |
| ChEMBL activity | `https://www.ebi.ac.uk/chembl/api/data/activity/{id}.json` (split comma-separated ids) |
| PubMed | `https://pubmed.ncbi.nlm.nih.gov/{pmid}/` |
| Paper | `https://doi.org/{id without "doi:"}` |
| Opentrons spec | `https://docs.opentrons.com/flex/system-description/pipettes/` |
| Simulator, simulated, assumed | no link |

- Dev guard: in development builds, a `<Num>` without provenance gets a 2 px magenta outline and a console warning. A vitest renders the workspace with a recorded run and asserts every `[data-num]` element has a `[data-provenance]` attribute.
- Before shipping, open one link of each kind with the Playwright MCP and confirm it loads.

## 6. Visual design system

Color tokens (in `src/design/tokens.css`, nowhere else):

| Token | Hex | Use |
|---|---|---|
| `--bench` | #E6EBE9 | page background |
| `--sheet` | #F9FAF9 | notebook surface, popovers |
| `--deck` | #D5DCDA | Flex deck base |
| `--slot` | #C7D0CE | slot recesses |
| `--rule` | #C3CBC9 | dividers, slider tracks, empty well rings |
| `--ink` | #1C2430 | text, primary buttons, key marks |
| `--graphite` | #5B6573 | secondary text, axes, inactive marks |
| `--active` | #D2457F | resorufin pink, 100% target activity |
| `--inhibited` | #3552A0 | resazurin blue, 0% target activity |
| `--ok` | #2F7D5B | verified |
| `--partial` | #C98A12 (marks), #8F6200 (text) | partly verified |
| `--flag` | #B8382F | not verified, failures |

- Activity ramp: `interpolateLab(--inhibited, --active)` over 0-100% activity. The colors borrow the resazurin viability assay, where wells stay blue where the compound shut things down and turn pink where activity remains. Use pink and blue only for data marks, never for small text or UI chrome.
- Contrast on `--sheet`: ink about 15:1, graphite 5.7:1, ok 4.8:1, partial text 5.1:1, flag 5.5:1. Graphite on `--bench` 4.9:1.
- Patterns: simulated values sit on a 45 degree hatch (graphite 1 px lines every 6 px at 35% opacity). Assumed values use a dotted outline.

Type (Archivo for the system's voice, Newsreader only for words quoted from papers):

| Role | Family | Weight | Width | Size / line | Notes |
|---|---|---|---|---|---|
| Product name | Archivo | 600 | 112% | 18 / 24 | |
| Question field | Archivo | 450 | 100% | 21 / 28 | |
| Stage numeral (margin) | Archivo | 500 | 75% | 36 / 36 | graphite |
| Section title | Archivo | 600 | 100% | 24 / 30 | |
| Body | Archivo | 400 | 100% | 16 / 24 | 68ch max |
| Captions, small UI | Archivo | 450 | 100% | 14 / 20 | |
| Deck, plate and axis labels | Archivo | 500 | 75% | 12 / 16 | |
| Headline number | Archivo | 700 | 118% | 48 / 52 | |
| Readout numbers | Archivo | 650 | 112% | 28 / 32 | |
| Paper quotes | Newsreader | 400 | n/a | 18 / 28 | the only serif |
| Code | ui-monospace, SFMono-Regular, Menlo, monospace | 400 | n/a | 13 / 20 | protocol viewer only |

- Scale: 12, 14, 16, 18, 21, 24, 28, 36, 48. Letter spacing -0.01em at 28 px and up, 0 elsewhere. No all caps anywhere. All numbers `font-variant-numeric: tabular-nums lining-nums`. Set width with `font-stretch`.
- Space: 4 px base, steps 4, 8, 12, 16, 24, 32, 48, 64. Stages sit 64 px apart.
- Radius by role: 2 px inputs and chips, 6 px buttons, slots and popovers, 14 px the deck base. Borders are 1 px `--rule` and only where they separate things. Shadow only on popovers and a dragged slider thumb: `0 6px 20px rgba(28, 36, 48, 0.18)`.
- Buttons: primary is ink fill with sheet text, 40 px tall. Secondary is a 1 px ink outline. Text buttons underline on hover. No icons in buttons except play and pause.
- Sliders: 2 px `--rule` track, ink fill to the value, 16 px sheet thumb with a 2 px ink ring, the designed value as a 1 x 8 px graphite tick.
- Focus: 2 px ink outline with a 2 px offset.
- Charts: hand-built SVG, 1 px graphite axes, 3 to 5 ticks, no gridlines except a faint baseline, square bar ends, hit areas at least 24 px, widths from a ResizeObserver with a 280 px minimum.

Banned, because they read as AI-generated defaults: cream backgrounds with terracotta accents, near-black with acid green, broadsheet hairline layouts, identical rounded cards with the same soft shadow, gradient washes, glassmorphism, all-caps or letter-spaced eyebrow labels, middle-dot meta strings ("A · B · C"), "WORD - fragment" labels, em dashes in UI copy, monospace for data labels, arrows in button or link text, emoji, sparkle icons, "AI-powered", fade-and-slide-up on every section, hover lifts on panels, parallax, radar charts, gauges, donuts, one accented word inside a headline, centered hero text, skeleton shimmer everywhere.

## 7. Motion

### 7.1 The run reveal (the only automatic choreography)

| Order | Notebook | Bench | Duration |
|---|---|---|---|
| 1 | Topic block opens. Count bars grow from the baseline, 30 ms stagger. Momentum marker slides to its value. | nothing | 600 ms |
| 2 | Design block opens. Ladder dots appear left to right. | Labware drops into D1, D2, D3, A3 (spring, 80 ms stagger). Plate wells tint column by column, 40 ms stagger. | 700 ms |
| 3 | Robot verdict appears. Cost numbers tween up. | The head parks over D1 with one small settle. | 500 ms |
| 4 | Uncertainty headline tweens. Sample dots drop into the chart, all within 1.2 s. p90 line slides in. | nothing | 1,200 ms |

Stages start 350 ms apart. In async mode each stage plays when its report arrives.

### 7.2 Motion that answers the user

| Action | Motion |
|---|---|
| Weight slider | Contribution segments spring to new widths, total tweens 200 ms |
| Lab-control drag | Wells add or remove with a 150 ms scale, ladder dots spring, server numbers dim |
| Results arrive | Numbers tween 300 ms, ghost of the previous p90 fades over 1.5 s |
| Replay | Head travel 350 ms ease-in-out at 1x, actions 250 ms, scaled by speed |
| Popover | 120 ms fade with a 4 px offset |
| Pin | The readout's numbers fly into a new chip (shared layout, 300 ms) |
| Explore this topic | The neighbor's name moves into the question field (shared layout, 350 ms) |

Durations: 120 ms fast, 220 ms base, 350 ms travel. Easing `cubic-bezier(0.2, 0, 0, 1)`. Springs: stiffness 380, damping 36. Constants live in `src/design/motion.ts`.

### 7.3 Reduced motion

With `prefers-reduced-motion: reduce` (use motion's `useReducedMotion` and a CSS media query): no travel, no stagger, no tweens. State changes apply instantly with at most a 150 ms opacity fade. The replay still steps and updates its log line.

## 8. Copy

| Where | Text |
|---|---|
| Start label | What do you want to test? |
| Start helper | Describe a target, a compound class or a disease mechanism. Lab Planner checks how crowded the topic is, designs a first dose-response experiment for an Opentrons Flex robot, runs it in the Opentrons simulator, and estimates how much real-world noise will blur the answer. |
| Examples | HER2 kinase inhibitors in breast cancer. p38 MAPK inhibitors in inflammation. JAK inhibitors in autoimmune disease. |
| How it works | 1 Checks how crowded the topic is in OpenAlex. 2 Designs a first dose-response experiment from published ChEMBL measurements and checks every citation. 3 Runs the protocol in the Opentrons simulator. 4 Simulates the experiment many times with real-world noise to show how far off the answer could be. |
| Run button | Run, while running: Running |
| Running line | Running all four stages. Usually a few seconds, longer on the first run of the day. |
| Stage names | Topic, Design, Robot check, Uncertainty |
| Blocked | Lab Planner doesn't design experiments for this topic. It designs in-vitro dose-response experiments for benign targets. |
| Offline topic | OpenAlex couldn't be reached, so topic numbers aren't shown. The experiment below doesn't depend on them. |
| Example pair notice | Your question didn't match a prepared compound and target, so this design uses lapatinib on HER2 as a worked example. |
| IC50 | IC50 is the concentration that cuts the target's activity in half. Lower means more potent. |
| Review summary | {n} of {total} evidence items verified |
| Status labels | Verified record, Verified quote, Partly verified, Not verified |
| Model text label | Model's note, not verified |
| Replay caption | Replay of the Opentrons simulator run. No physical robot was used. |
| Replay unavailable | Replay needs step details from the server (backend item B0.4). |
| Audit clean | Every well ends as planned. |
| Uncertainty label | Simulated, seed {seed}, {runs} runs |
| Headline sentence | In 9 of 10 simulated experiments, the measured IC50 lands within {p90}x of the true value. Half land within {median}x. |
| Calibration | Checked against real data: the 90% range contained {coverage}% of {pairs} held-out ChEMBL measurements. The target is 90%. |
| Buttons | Explore this topic, Reset weights, Try this change, Pin for comparison, Reset to designed values, View protocol, Replay robot run, Skip to end, Share, Ask a different question, Open a recorded run |
| Share toast | Link copied |
| Server down | Can't reach the Lab Planner server at {base}. Start it with uvicorn backend.api:app --reload, or open a recorded run. |
| Cold start | The server is waking up. Free hosting can take up to a minute. |
| Bad response | The server sent a run the dashboard can't read: {path}. |

Number formats (`src/lib/format.ts`): concentrations in nM with thousands separators from 1,000 up ("2,399 nM"), 3 significant digits from 1 to 999 ("24.0 nM"), 2 below 1 ("0.12 nM"). Volumes "50 µL". Fold error "1.31x". Shares as whole percents unless below 1% ("0.5%"). Negative numbers with an ASCII hyphen.

## 9. Accessibility, responsive, performance

- Every control is reachable by keyboard. Radix sliders take arrows, Page Up and Page Down, Home and End. Popovers open with Enter and close with Esc. The plate map is one focus stop, arrows move a highlighted well, and an aria-live region reads the well.
- Charts have an `aria-label` summary and a visually hidden data table. Badges carry text. The replay announces the current step in a polite live region, at most once per second.
- Color never carries meaning alone.
- Check at 390, 768, 1024 and 1440 px. No horizontal scroll at 390 px.
- The deck SVG stays under 400 nodes. Plate cells are memoized. Replay timing runs on motion's animation frames.

## 10. Code structure

```
frontend/
  index.html, vite.config.ts, .env.example, playwright.config.ts
  scripts/record-demo.mjs
  public/demo/index.json, public/demo/*.json
  src/
    main.tsx, App.tsx
    api/       client.ts, capabilities.ts, normalize.ts, schemas.ts, types.ts, queries.ts
    state/     store.ts
    lib/       matrix.ts, dilution.ts, hill.ts, plate.ts, whatif.ts, replay.ts, audit.ts,
               provenance.ts, format.ts, labware.ts, planner.ts, hash.ts
    design/    tokens.css, motion.ts, fonts.ts, global.css
    components/
      Num/ (Num, ProvenancePopover)
      Shell/ (TopBar, QuestionBar, StageStrip, Banner, StartScreen, HistoryDrawer)
      Topic/ (CountsChart, MomentumScale, CrowdingVerdict, NeighborList, ExploredTopics)
      Matrix/ (MatrixTable, WeightSlider, ContributionBar)
      Design/ (PairHeader, StartingGuess, DilutionLadder, PlateMap, DesignFacts)
      Review/ (ReviewThread, EvidenceTurn, RuleChecks, SkepticTurn, StatusBadge)
      Robot/ (SimVerdict, CostStrip, RunLog, ProtocolViewer)
      Bench/ (Bench, Deck, TipRack, Plate96, Reservoir12, TrashBin, PipetteHead, ReplayControls, PlateAudit)
      Uncertainty/ (SimulatedBlock, Headline, FoldErrorDots, CurveBand, NoiseTable, Calibration, NextChanges, CompareChart)
      Controls/ (LabControls, ControlSlider, Readout, PinTray)
    test/ (unit and property tests)
  e2e/ smoke.spec.ts
```

State (zustand): `question`, `settings {runs, seed, readerCv}`, `weights`, `run` (normalized run or null), `origin ("live" or "recorded")`, `whatIf {base, draft, notes}`, `pins`, `replay {status, index, speed}`. Server data stays in React Query. `lib/` files are pure functions with no React imports.

## 11. Kiro setup

### 11.1 Spec

Update `.kiro/specs/dashboard/requirements.md`, and create `design.md` and `tasks.md` in the same folder, from this brief. Requirements use EARS ("WHEN the user releases a lab-control slider THE SYSTEM SHALL send the patched design to POST /api/uncertainty and show the new p90 fold error"). Number them R1 to R15 to match sections 5.1 to 5.15, with R0 for section 0. `design.md` covers architecture, data flow, the API adapter, components and tokens. `tasks.md` lists the section 12 tasks with P0, P1 or P2 tags and the requirement ids each one satisfies.

### 11.2 Steering

Create `.kiro/steering/ui.md` with exactly this content:

```markdown
---
inclusion: fileMatch
fileMatchPattern: "frontend/**"
---
# Lab Planner UI rules

Full spec: frontend/BRIEF.md. These rules apply to every file under frontend/.

## Honesty
- Every number renders through <Num> with a source, simulated or derived provenance. No bare numbers in JSX.
- Never invent data, progress percentages or placeholder charts. Missing data gets one plain sentence saying what is missing.
- Model-written text is never shown as verified. Only RationaleItem.status decides a badge.
- The replay always says it replays the Opentrons simulator run.
- No third-party logos.
- Backend quirks are handled in src/api/normalize.ts only.

## Look
- Colors come from src/design/tokens.css only. No raw hex in components.
- Archivo Variable everywhere, width by role (75% labels, 100% UI, 112-118% display numbers). Newsreader Variable only for quotes from papers. Monospace only in the protocol viewer.
- Tabular numerals for every number.
- Radius by role: 2px inputs, 6px buttons, slots, popovers, 14px deck. Shadows only on popovers and a dragged thumb.
- Pink and blue are data colors for target activity. Never use them for UI chrome.

## Banned
Cream with terracotta. Near-black with acid green. Identical rounded cards with the same soft shadow. Gradient washes. Glassmorphism. All-caps or letter-spaced labels. Middle-dot meta strings. Em dashes in UI copy. Monospace data labels. Arrows in button text. Emoji. Sparkle icons. "AI-powered". Fade-and-slide-up on every section. Hover lifts on panels. Parallax. Radar charts, gauges, donuts. One accented word in a headline. Centered hero text. Skeleton shimmer.

## Copy
Sentence case. Plain verbs. Buttons name the action. Errors say what happened and what to do next. No exclamation marks.

## Motion
- The run reveal (BRIEF 7.1) is the only automatic choreography. Everything else answers a user action.
- 120 ms fast, 220 ms base, 350 ms travel. Springs stiffness 380, damping 36.
- prefers-reduced-motion: no travel, instant state changes, at most a 150 ms fade.

## Accessibility
Visible focus (2px ink outline, 2px offset). Color never carries meaning alone. Every control works by keyboard. Charts have text summaries. No horizontal scroll at 390px.
```

### 11.3 Hooks

Create each one with "Ask Kiro to create a hook" in the Agent Hooks panel, so Kiro writes its own config under `.kiro/hooks/`. Kiro's file triggers fire on edits the agent makes, not on manual saves.

| Hook | Trigger | Files | Action |
|---|---|---|---|
| Typecheck on save | File save | `frontend/src/**/*.ts`, `frontend/src/**/*.tsx` | command `npm --prefix frontend run typecheck` |
| Logic tests on save | File save | `frontend/src/lib/**` | command `npm --prefix frontend run test -- src/lib` |
| Contract sync | File save | `backend/contracts/**/*.py` | agent prompt: "A backend contract changed. Update frontend/src/api/types.ts, schemas.ts and normalize.ts to match, keeping old fields readable. If the API is running, run npm --prefix frontend run gen:api." |
| UI review | Manual | none | agent prompt: "Open http://localhost:5173 with the Playwright MCP at 1440x900 and 390x844. Run the demo script in frontend/BRIEF.md section 13. Save screenshots to frontend/screenshots/. Review them against the Banned list in .kiro/steering/ui.md and the 13 checks. List each violation with its file, then fix it." |

### 11.4 MCP

Open "Kiro: Open workspace MCP config (JSON)" and set `.kiro/settings/mcp.json` to:

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["-y", "@playwright/mcp@0.0.83"]
    }
  }
}
```

Use it for the UI review hook, the provenance link check (5.15) and the write-up screenshots.

### 11.5 Property-based tests

Write the Appendix B properties with fast-check in `src/test/`. They double as the PBT evidence for the Kiro write-up.

### 11.6 For the Kiro write-up

Keep `.kiro/` committed (not gitignored). Take screenshots of the spec files, a hook firing, the steering file and a Playwright MCP session.

## 12. Build order

Times assume Kiro starts at 2:50 PM and the team's 4:00 PM feature freeze. If the freeze moves, P1 moves with it. P2 happens only after the freeze if the team agrees.

| ID | Task | Requirements | Done when |
|---|---|---|---|
| P0-1 | Scaffold, exact versions, tokens, fonts, two-column shell, start screen | R0, R1, R6 | start screen matches section 4 at 1440 and 390 px |
| P0-2 | API client, capabilities, normalize, zod schemas, banners, recorded-run loader, record-demo script | R1, R14 | a recorded run renders with the backend off |
| P0-3 | `<Num>` and the provenance popover, dev guard and its test | R15 | the provenance test passes |
| P0-4 | Topic block, matrix with weight sliders | R4, R6 | weights recompute instantly, client total equals server total |
| P0-5 | Design block: pair header, starting guess, ladder, plate map, facts | R7 | plate map shows the planned layout with hover details |
| P0-6 | Review thread with badges, red flags and rule checks | R8 | the unverified fixture shows the flag and reason |
| P0-7 | Robot check and the uncertainty block (numbers, noise, calibration, next changes list) | R9, R11 | every number has provenance |
| P0-8 | Lab controls with what-if requests, live geometry, readout | R12 | the 5.12 acceptance passes |
| P0-9 | Static bench deck with labware and mini plate | R10 | deck renders with and without `sim.deck` |
| P1-1 | Replay and plate audit (when steps are structured) | R10 | replay runs at 16x, audit lists the current compiler's issues |
| P1-2 | Run reveal choreography and reduced motion | R2 | matches 7.1, reduced motion verified |
| P1-3 | Try this change, pin, cost against certainty chart | R13 | two pins plot, frontier draws |
| P1-4 | Pivot list (when neighbors exist), history, `?run=` and Share | R5, R14 | reload by link works |
| P2 | Async progress, fold-error dots, curve band, protocol viewer, model card metrics, evidence drawer, skeptic turns, explored-topics matrix, pair picker | R2, R4, R5, R7, R8, R9, R11 | each behind its capability flag |

## 13. Acceptance checklist and demo script

1. The start screen renders with no console errors.
2. Click "HER2 kinase inhibitors in breast cancer". All four stages render, and the reveal plays in order.
3. Hover a count bar, momentum, each matrix axis, the starting guess, each cost number, the fold error and the calibration. Each opens a popover with a source.
4. Drag the Momentum weight to 0. The total changes at once and the bar animates.
5. Change Concentrations from 10 to 8. The plate map updates at once. About 2 s after release the fold error updates, with the old value ghosted.
6. Click "Try this change" on the first suggestion. The controls move and the numbers recompute.
7. Pin two designs. The chart shows both.
8. Press Replay at 16x. The head moves, tips leave the rack, wells recolor left to right, the log line follows, and the audit appears at the end.
9. Stop the backend. The banner appears. "Open a recorded run" works.
10. Ask "gain of function influenza". The blocked panel shows its reason and nothing else.
11. Tab from the question to Run to the sliders to a popover. Arrows move sliders, Enter opens a popover, Esc closes it. Focus is always visible.
12. At 390 px there is no horizontal scroll and the bench stacks.
13. With reduced motion on, nothing travels and all content shows.
14. Screenshots pass the Banned list in the steering file.

## Appendix A. Wire types (today plus announced additions)

Fields marked "added" may be missing. Read them as optional.

```ts
export type SourceType =
  | "openalex" | "pubmed" | "chembl_activity" | "semantic_scholar" | "paper"
  | "spec" | "simulator" | "simulated" | "assumed"   // "assumed" added B0.2

export interface Source { type: SourceType, id: string, url?: string | null }

export interface SafetyGate { pass?: boolean, passed?: boolean, reasons: string[] }

export type AxisKey = "momentum" | "novelty" | "evidence" | "automatable" | "cost_time"

export interface TopicReport {
  query: string
  topic: { openalex_id: string, name: string }
  counts_by_year: { year: number, works: number, source: Source }[]
  momentum: { p_growth: number, model: string }
  neighbors: { openalex_id: string, name: string, works_last_5y: number, p_growth?: number | null }[]
  matrix: Record<AxisKey, number> & {
    weights: Record<AxisKey, number>
    total: number
    axis_sources?: Partial<Record<AxisKey, Source>>   // added B0.2
    axis_notes?: Partial<Record<AxisKey, string>>     // added B0.2
  }
  safety: SafetyGate
  offline?: boolean                                    // added B0.2
}

export interface RationaleItem {
  claim: string
  pmid: string
  evidence_type: "chembl_activity" | "abstract_quote" | string
  evidence_id: string
  quote?: string | null
  model_note?: string | null
  status: "verified" | "partial" | "unverified" | string
  reason?: string | null
  verified: boolean
  url?: string | null                                  // added B1.6
  document_chembl_id?: string | null                   // added B1.6
}

export interface ReviewTurn {                          // added B2.5
  role: "skeptic", argument: string, field: string, proposed_value: number
  p90_before: number, p90_after: number, extra_tips: number, extra_compound_uL: number
  verdict: "supported" | "not supported"
}

export interface ExperimentDesign {
  design_id: string
  topic_id: string
  assay: { type: string, readout: string, target_chembl_id: string, compound_chembl_id: string }
  prior_ic50: { median_nM: number, n_measurements: number, spread_log10: number, source: Source }
  dilution: { top_nM: number, factor: number, points: number }
  replicates: number
  controls: { positive_wells: number, negative_wells: number }
  plate: { labware: string, layout: string }
  volumes_uL: { transfer: number, diluent: number }
  pipette: string
  tiprack: string
  rationale: RationaleItem[]
  notes?: string[]
  review?: ReviewTurn[]                                // added B2.5
}

export interface StepLocation { slot: string | null, well: string | null, labware: string | null }

export interface ProtocolStep {
  i: number
  action: string            // today a first word, after B0.4 one of pick_up_tip, drop_tip, aspirate,
                            // dispense, mix, transfer, blow_out, touch_tip, move_to, other
  uL?: number | null
  labware?: string | null
  well?: string | null
  level?: number            // added B0.4
  text?: string             // added B0.4
  slot?: string | null      // added B0.4
  source?: StepLocation | null
  dest?: StepLocation | null
  repetitions?: number | null
}

export interface DeckSlot {                            // added B0.4
  slot: string, load_name: string, display_name: string
  role: "tips" | "plate" | "reservoir" | "trash"
  contents?: Record<string, string>
}

export interface SimResult {
  design_id: string
  protocol_file: string
  simulator: { pass?: boolean, passed?: boolean, error: string | null, log_lines: number, seconds: number, opentrons_version: string }
  cost: { tips: number, compound_uL: number, plates: number, robot_steps: number, source?: Source | null }  // source added B0.5
  steps: ProtocolStep[]
  deck?: DeckSlot[]                                    // added B0.4
}

export interface NextExperiment {
  change: string
  p90_fold_error_drop_pct: number
  extra_tips: number
  extra_compound_uL: number
  extra_plates: number
  score: number
  design?: ExperimentDesign | null                     // added B1.2
  p90_after?: number | null                            // added B1.2
}

export interface UncertaintyReport {
  design_id: string
  label: string
  runs: number
  seed: number
  noise: {
    lab_spread_log10: number, pipette_cv: number, pipette_bias: number, reader_cv: number
    sources: Source[]
    field_sources?: Partial<Record<"lab_spread_log10" | "pipette_cv" | "pipette_bias" | "reader_cv", Source>>  // added B0.8
  }
  fold_error: { median: number, p90: number }
  outside_range_share: number
  failed_fit_share: number
  calibration: { coverage_90: number, pairs: number }
  next_experiments: NextExperiment[]
  samples?: { true_ic50_nM: number[], recovered_ic50_nM: number[], fold_error: number[] } | null   // added B1.3
  curve?: { concentrations_nM: number[], activity_p10: number[], activity_p50: number[], activity_p90: number[] } | null  // added B1.3
}

export interface PairInfo {                            // added B0.1 and B0.3
  label: string, compound_chembl_id: string, target_chembl_id: string
  compound_name: string, target_name: string, match: "user" | "query" | "default"
}

export interface RunResponse {
  run_id: string
  blocked: boolean
  status?: string                                      // added B0.1
  pair?: PairInfo | null
  topic: TopicReport | null
  design: ExperimentDesign | null
  sim: SimResult | null
  uncertainty: UncertaintyReport | null
}

export interface RunRecord extends RunResponse {
  meta: { run_id: string, query: string, created_at: string, status: string }
}

export interface RunRequest {
  query: string
  weights?: Record<AxisKey, number>
  runs?: number
  seed?: number
  reader_cv?: number
  compound_chembl_id?: string | null                   // added B0.3
  openalex_topic_id?: string | null                    // added B2.2
  mode?: "sync" | "async"                              // added B2.1
}

export interface WhatIfRequest {
  design: ExperimentDesign
  runs?: number
  seed?: number
  reader_cv?: number
  plan?: boolean                                       // added B0.9
}
```

## Appendix B. Formulas and properties

Each formula is a pure function in `src/lib/`. Each "Property" line is a fast-check test.

B.1 Matrix total. `total = sum(axis_k x w_k) / sum(w_k)` over the five axes, and 0 when the weights sum to 0. Contribution of axis k = `axis_k x w_k / sum(w)`. Property: total stays in [0, 1], contributions sum to the total, scaling every weight by the same positive number leaves the total unchanged, default weights reproduce the backend's total within 1e-6.

B.2 Concentrations. `c_i = top_nM / factor^i` for i = 0 to points - 1. Property: strictly decreasing, `c_0 = top_nM`, each neighbor ratio equals the factor.

B.3 Coverage of the starting guess. `above = log10(top / prior)`, `below = log10(prior / bottom)`. For lapatinib today: above 2.00, below 2.29.

B.4 Designer's target half-width. `h = max(2, 1.645 x spread_log10)` (backend designer.py). The rule check passes when `min(above, below) >= h - 0.01`.

B.5 Expected activity. `a(c) = 100 / (1 + (c / ic50)^1)`, Hill slope 1 as in the backend engine. Property: 50 at c = ic50, strictly decreasing in c, always inside (0, 100).

B.6 Activity color. `interpolateLab(--inhibited, --active)(a / 100)`.

B.7 Planned layout (matches backend item B1.1). Replicate r (0-based) uses row `"ABCDEFGH"[r]`. Point i uses column i + 1. Negative controls fill column 12 from row A, positive controls continue below them. Valid when points <= 11, replicates <= 8, positive + negative <= 8. Wells used = points x replicates + positive + negative. Property: no two planned wells share a position and all sit inside 8 x 12.

B.8 applyWhatIf(design, patch). Apply the patch, then `diluent = transfer x (factor - 1)`. If `transfer x factor > 300`, set `transfer = floor(300 / factor)` and add a note. Clamp to the 5.12 ranges and the B.7 limits, with a note for each clamp. Give the result a new `design_id` (B.12). Property: the output always satisfies every limit, `(transfer + diluent) / transfer` equals the factor within 1e-9, applying the same patch twice equals applying it once, and fields outside the patch stay unchanged except diluent and design_id.

B.9 Replay state. Each well holds `{volume_uL, conc_nM}`. Reservoir A1 starts as diluent (large volume, 0 nM). Reservoir A2 starts as stock at `top_nM`. `aspirate` moves volume from the well into the tip at the well's concentration. `dispense` mixes by volume: `conc = (v1 c1 + v2 c2) / (v1 + v2)`. `drop_tip` discards what the tip holds. `blow_out` empties the tip into its location. A volume that would go negative clamps to 0 and records a warning for the audit. Property: compound amount (volume x concentration, summed over wells, tip and discarded liquid) is conserved across every step, and no volume is ever negative.

B.10 Plate audit. Compare the replay's final state with B.7. Each planned dilution well should hold the diluent volume (within 1 µL) at `c_i` (within 1%). Each control should hold the diluent volume at 0 nM (negative) or `top_nM` (positive). Report empty wells, wrong volumes, wrong concentrations, unfilled planned wells and wells filled outside the plan, one plain sentence each.

B.11 Planner label parser (fallback until `next.design` exists). Patterns: `add 1 replicate \((\d+) total\)` sets replicates, `add 2 dilution points` adds 2 to points, `tighten dilution factor to ([\d.]+)` sets the factor, `raise transfer volume to ([\d.]+)` sets the transfer. Anything else is shown without a "Try this change" button.

B.12 Hashing. Stable JSON (sorted keys) of the request body, then FNV-1a 32-bit, then the first 6 hex characters. What-if `design_id = ${base}-w${hash6}` where base is the run's design id.

B.13 Fold spread. `fold = 10^spread_log10` (0.932 gives 8.55, shown as "about 8.6-fold").

B.14 Excess-error drop. `(p90_before - p90_after) / (p90_before - 1)`, the same formula as the backend planner.

## Appendix C. Backend items this brief depends on

backend/DASHBOARD_GAPS.md has the full list for the backend owner. The ones that change what judges see the most: B0.3 (the design matches the question), B0.4 (replay), B0.5 (cost from the simulator), B0.7 (pipette numbers match the Opentrons spec they cite) and B1.1 (all replicates and controls actually get pipetted, which is also what the plate audit checks).
