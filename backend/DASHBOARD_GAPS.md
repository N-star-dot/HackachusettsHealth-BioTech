# Backend changes the dashboard needs (prompt for Kiro)

How to use: open this repo in Kiro and say "Read backend/DASHBOARD_GAPS.md and implement B0 in order, one commit per item, with the test listed for each." Then B1, then B2 only if time allows.

Written Sat 2026-10-24, 2:40 PM, against commit d2d4406. Every problem below was found by reading the backend code and by running the compiler's current protocol (lapatinib design: 10 points, 50 µL transfer, 100 µL diluent) through the real Opentrons 10.1.0 simulator.

The dashboard spec is frontend/BRIEF.md. It detects each change below at runtime (BRIEF section 3.3), so ship items as they are ready. Field names here and in the brief must stay identical.

## Rules for every item

1. Additive only. Never rename or remove an existing contract field. New fields get defaults, so mocks/ and tests/ keep passing. Update mocks/*.json when you add fields and keep tests/test_mocks_validate.py green.
2. Every number the dashboard shows needs a Source, or must sit inside a block labeled simulated. A value we chose ourselves gets the new source type `assumed` (B0.2).
3. One commit per item, each with its test. Run `python -m pytest -q` before each commit.
4. Do not touch frontend/.

## B0. Unblock the dashboard (target 3:10 PM)

### B0.1 Typed responses, one JSON shape per run

Problem. /api/run and /api/run/{run_id} return plain dicts, so /openapi.json has no response schemas and the frontend cannot generate types. Also, POST /api/run dumps contracts by alias (`safety.pass`, `simulator.pass`), while GET /api/run/{run_id} returns the stored JSON, which `db.save_report` wrote with `model_dump_json()` (field names, so `safety.passed`, `simulator.passed`). The same run comes back in two shapes.

Change in backend/api/app.py:
- Add response models and set `response_model` on every route:
  - `PairInfo {label: str, compound_chembl_id: str, target_chembl_id: str, compound_name: str, target_name: str, match: Literal["user", "query", "default"]}`
  - `RunResponse {run_id: str, blocked: bool, status: str = "done", pair: PairInfo | None = None, topic: TopicReport | None, design: ExperimentDesign | None, sim: SimResult | None, uncertainty: UncertaintyReport | None}`
  - `RunMeta {run_id: str, query: str, created_at: str, status: str}`
  - `RunRecord(RunResponse)` plus `meta: RunMeta`
  - POST /api/uncertainty: `response_model=UncertaintyReport`. GET /api/health: `{status: str}`.
- In GET /api/run/{run_id}, validate each stored payload with its contract model (`TopicReport.model_validate(...)` and so on) before returning. FastAPI then dumps by alias exactly like POST. SafetyGate and SimulatorInfo already set `populate_by_name=True`, so stored `passed` validates.
- Persist the pair info as one more report stage, `"pair"` (the reports table is keyed by stage, so no schema change).

Test. POST a run, GET it by id, assert both bodies have the same keys at every level and that `topic.safety` has `pass`. Assert `/openapi.json` has `components.schemas.RunResponse`.

### B0.2 Honest stage 1

Problems.
- When OpenAlex is unreachable, `_placeholder_counts` invents counts (`max(50, 800 - (2024 - y) * 40)`) and labels them `source.type = "openalex"`, id `T00000`. The momentum model then scores the invented series.
- Matrix axes other than momentum are constants: novelty 0.55, evidence 0.40, automatable 1.0, cost_time 0.62.
- `neighbors` always holds `Neighbor(openalex_id="T00001", name="placeholder neighbor", works_last_5y=340, p_growth=0.64)`.

Change:
- contracts/common.py: add `SourceType.ASSUMED = "assumed"` (a value we chose, not measured).
- TopicReport: add `offline: bool = False`. Placeholder counts get `Source(type="simulated", id="offline-placeholder")`, the report gets `offline=True`, and momentum gets `model="offline-placeholder"`.
- ViabilityMatrix: add `axis_sources: dict[str, Source] = {}` and `axis_notes: dict[str, str] = {}`.
  - momentum: `Source(type="openalex", id=<topic id>, url=<counts url from B1.6>)`, note "Trained model hgb-v3 scored this topic's 2015-2024 OpenAlex counts".
  - each constant axis until B1.5 computes it: `Source(type="assumed", id="fixed-prior")`, note "Fixed value, not computed from this topic yet".
- neighbors: return `[]` until B2.2 computes real ones.

Test. Monkeypatch `openalex.search_topics` to raise. The report has `offline` true, every count source is `simulated`, `neighbors == []`, and every non-momentum `axis_sources` entry is `assumed`.

### B0.3 Pick the compound-target pair from the question

Problem. The orchestrator calls `get_demo_pair()` and `design_experiment()` with no arguments, so every question, including "JAK inhibitors", gets lapatinib on HER2.

Change:
- RunRequest: add `compound_chembl_id: str | None = None`.
- stage2_design/demo_pairs.py: add `match_pair(query, compound_chembl_id) -> tuple[dict, str]`. Case-insensitive, word-boundary keyword match:

| Pair | compound_chembl_id | Keywords |
|---|---|---|
| lapatinib on HER2 | CHEMBL554 | her2, erbb2, lapatinib |
| SB-203580 on p38alpha (MAPK14) | CHEMBL10 | p38, mapk14, sb-203580, sb203580 |
| tofacitinib on JAK2 | CHEMBL221959 | jak, jak2, janus kinase, tofacitinib |

  A given `compound_chembl_id` wins (match `"user"`). Else the first keyword hit (match `"query"`). Else the first pair (match `"default"`).
- Pass the chosen compound id into `design_experiment(compound_chembl_id=...)`, `get_demo_pair(...)` and `evidence_abstracts_for(...)`.
- Names: split the pair label on `" on "` ("lapatinib", "HER2").
- New GET /api/pairs returns `[{label, compound_chembl_id, target_chembl_id, compound_name, target_name, prior: {median_nM, spread_log10, n_papers, papers: [{document_chembl_id, activity_id, value_nM, pchembl_value}]}}]` from data/demo/demo_pairs.json.

Test. "JAK inhibitors in autoimmune disease" designs for CHEMBL221959 with match `"query"`. "protein folding" gets match `"default"`. `compound_chembl_id="CHEMBL10"` gets match `"user"`.

### B0.4 Structured robot steps for the replay

Problem. `_extract_steps` keeps only the first word of each log line, lowercased ("picking", "aspirating"), with no volume, slot or well. The dashboard cannot replay that.

Facts from the real simulator (Opentrons 10.1.0, current template, lapatinib design):
- `run_log` is a flat list of 142 dicts, each `{level, payload, logs}`. `level` is nesting depth: 21 entries at 0, 67 at 1, 54 at 2. No `subcommands` key.
- `payload` has `text` plus structured keys. Aspirate and dispense: `volume, location, rate, end_location, instrument`. Transfer: `volume, source, dest, locations`. Mix: `repetitions, volume, location`. Pick up and drop: `location, instrument`.
- `str(payload["location"])` looks like `A1 of NEST 12 Well Reservoir 15 mL on slot D3`. The trash is `Trash Bin on slot A3`.
- Example lines: `Picking up tip from A1 of Opentrons Flex 96 Tip Rack 200 µL on slot D1`, `Aspirating 50.0 uL from A1 of Corning 96 Well Plate 360 µL Flat on slot D2 at 716.0 uL/sec`, `Mixing 3 times with a volume of 50.0 ul`, `Dropping tip into Trash Bin on slot A3`.

Change:
- ProtocolStep: add, all optional with defaults, `level: int = 0`, `text: str = ""`, `slot: str | None = None`, `source: StepLocation | None = None`, `dest: StepLocation | None = None`, `repetitions: int | None = None`, with `StepLocation {slot: str | None, well: str | None, labware: str | None}`. Keep `i, action, uL, labware, well`.
- Fill from payload fields first, text only as a fallback:

```python
_LOC = re.compile(r"^(?P<well>[A-P]\d{1,2}) of (?P<labware>.+?) on slot (?P<slot>[A-D][1-4])$")
_SLOT_ONLY = re.compile(r"^(?P<labware>.+?) on slot (?P<slot>[A-D][1-4])$")
_ACTIONS = [
    ("Picking up tip", "pick_up_tip"), ("Dropping tip", "drop_tip"),
    ("Aspirating", "aspirate"), ("Dispensing", "dispense"), ("Mixing", "mix"),
    ("Transferring", "transfer"), ("Blowing out", "blow_out"),
    ("Touching tip", "touch_tip"), ("Moving to", "move_to"),
]
```

  `action` defaults to `"other"`. `uL` comes from `payload["volume"]`. Keep `text` verbatim.
- SimResult: add `deck: list[DeckSlot] = []` with `DeckSlot {slot: str, load_name: str, display_name: str, role: Literal["tips", "plate", "reservoir", "trash"], contents: dict[str, str] = {}}`. Fill it from a `DECK` constant next to the compiler template: A3 trash, D1 tips, D2 plate, D3 reservoir with `contents={"A1": "diluent", "A2": "compound"}`.
- Static fallback (opentrons not installed): return `steps=[]`, not the two invented steps it returns today. The dashboard then says replay is unavailable instead of replaying a fake run.

Test. Simulate the lapatinib design. `len(steps) == len(run_log)`. Step 0 is `pick_up_tip` at slot D1 well A1. Every aspirate and dispense has `uL`, `slot` and `well`. The count of `pick_up_tip` steps equals the count of lines starting "Picking up tip".

### B0.5 Cost counted from the run log

Problem. `_estimate_cost` reports tips = points + 2 = 12 and compound_uL = transfer x points = 500 µL. The simulator's own log for that protocol picks up 11 tips and aspirates 50 µL from the compound well (reservoir A2) once. The cost card disagrees with the simulated run.

Change:
- When the simulator ran, compute cost from the parsed steps: tips = count of `pick_up_tip`, compound_uL = sum of aspirate `uL` at slot D3 well A2, plates = 1, robot_steps = count of leaf actions (`pick_up_tip, aspirate, dispense, drop_tip, blow_out, touch_tip, move_to`).
- CostBreakdown: add `source: Source | None = None`. Simulator path: `Source(type="simulator", id=<protocol_file>)`. Static fallback keeps the formula with `Source(type="assumed", id="cost-formula")`.

Test. For the current template and the lapatinib design, tips == 11 and compound_uL == 50. After B1.1 changes the template, compute expected values from the run log in the test instead.

### B0.6 POST /api/simulate

Why. The lab controls need cost and a replay for a changed design. Compile plus simulate takes about 0.4 s.

Change. POST /api/simulate `{design: ExperimentDesign}` returns SimResult. Compile to `protocols/whatif/<first 12 hex of sha1 of the design JSON>.py`, so a what-if never overwrites `protocols/<design_id>.py`. Validate `design_id` against `^[A-Za-z0-9_-]{1,64}$` (the dashboard sends ids like `d-001-w3fa21c`).

Test. Posting the run's own design returns `pass` true and the same number of steps as the run.

### B0.7 Pipette error table must match the spec it cites

Problem. `noise_sources._PIPETTE_SPEC` does not match the published Opentrons numbers. For `flex_1channel_1000` it uses 1% CV and 1.5% bias for 10-99 µL, while the spec at 50 µL says 0.30% and 0.50%. It also has a 1 µL band, but that pipette's range starts at 5 µL. The dashboard shows these numbers with "Opentrons spec" as the source, so today the popover would be wrong.

Published values, page "Opentrons Flex: Pipettes", https://docs.opentrons.com/flex/system-description/pipettes/ (checked 2026-10-24):

| Pipette (range) | Tip | Volume | Random error (CV) | Systematic error |
|---|---|---|---|---|
| Flex 1-Channel 1000 µL (5-1000 µL) | 50 µL | 5 µL | 2.50% | ±5.00% |
| | 50 µL | 50 µL | 0.30% | ±0.50% |
| | 200 µL | 200 µL | 0.15% | ±0.50% |
| | 1000 µL | 1000 µL | 0.15% | ±0.50% |
| Flex 1-Channel 50 µL (1-50 µL) | 20 µL | 1 µL | 3.50% | ±8.00% |
| | 50 µL | 1 µL | 7.00% | ±8.00% |
| | 20 µL | 5 µL | 0.75% | ±1.50% |
| | 50 µL | 10 µL | 0.50% | ±1.50% |
| | 50 µL | 50 µL | 0.40% | ±1.25% |

Change. Replace the table with these rows. Use the nearest listed volume at or below the transfer volume (say so in the Source id, for example `flex_1channel_1000, nearest published point 50 µL`). Reject a transfer below the pipette's minimum with a ValueError that the API returns as 422 with a readable message. Set the Source url to the page above.

Test. `lookup_pipette_error("flex_1channel_1000", 50)` returns (0.003, 0.005). A 2 µL transfer on the 1000 µL pipette raises.

### B0.8 One source per noise number

Problem. `NoiseModel.sources` always lists the Kalliokoski paper and the spec. But `engine.run_uncertainty` uses `design.prior_ic50.spread_log10` (0.932 for lapatinib, measured across 21 ChEMBL papers) and only falls back to Kalliokoski's 0.68 when that is missing. The popover would credit the wrong source.

Change. NoiseModel: add `field_sources: dict[str, Source] = {}` with keys:
- `lab_spread_log10`: the prior's ChEMBL activity Source when the pair's spread is used, else the Kalliokoski DOI Source.
- `pipette_cv`, `pipette_bias`: the spec Source from B0.7.
- `reader_cv`: `Source(type="assumed", id="user setting, default 0.05")`.

Test. For the lapatinib design, `field_sources["lab_spread_log10"].type == "chembl_activity"`.

### B0.9 Fast what-if while a slider moves

Change. WhatIfRequest: add `plan: bool = True`. When false, skip `plan_next_experiments` (it reruns the Monte Carlo 3 or 4 more times). The dashboard sends `plan=false` while dragging and `plan=true` on release.

## B1. Make the experiment physically right (target 3:50 PM)

### B1.1 Compiler v2

Problems in the simulated run of today's template:
- Only row A is pipetted. The design asks for 3 replicates and 4 + 4 controls, and none of them are run.
- Top well A1 receives 50 µL of compound and then gives 50 µL to A2, so it ends empty. The highest concentration cannot be read.
- The last well (A10) ends with 150 µL while the others hold 100 µL.
- `dilution.factor` and the volumes can disagree. The Monte Carlo uses `factor`, the robot uses the volumes.

Target layout (the dashboard draws exactly this, BRIEF Appendix B):
- Replicate r (0-based) uses plate row `"ABCDEFGH"[r]`. Dilution point i uses column i + 1. Points at most 11, replicates at most 8.
- Column 12 holds controls: negative controls (diluent only) in the first `negative_wells` rows, positive controls (compound stock at top concentration) in the next `positive_wells` rows. `positive_wells + negative_wells` at most 8.

Target liquid handling per replicate row:
1. One tip: `diluent_uL` of diluent (reservoir A1) into columns 2 to points, `new_tip="never"`.
2. New tip: `transfer_uL + diluent_uL` of compound stock (reservoir A2, at `top_nM`) into column 1, so column 1 keeps `diluent_uL` after the first serial step.
3. Serial: `transfer_uL` from column i to i + 1 with `mix_after=(3, transfer_uL)`, new tip each step.
4. New tip: aspirate `transfer_uL` from the last column, then drop the tip, so every dilution well ends with `diluent_uL`.

Then controls: one tip for all negative wells (`diluent_uL` of diluent each), one tip for all positive wells (`diluent_uL` of stock each).

Also:
- Designer derives `diluent_uL = transfer_uL * (factor - 1)`. ExperimentDesign validates `abs((transfer + diluent) / transfer - factor) < 1e-6` and `transfer * factor <= 300` (360 µL well with margin).
- Tips needed = R x (P + 2) + (1 if negatives) + (1 if positives). If that exceeds 96, load a second tip rack in C1 and pass both racks to `load_instrument`. Report it in `deck`.
- Designer sets `plate.layout = "rows"`, so the contract stops claiming randomization.
- Add `cost_model(design)` in stage3_protocol: tips as above, compound_uL = R x (T + D) + positive_wells x D, plates = 1.

Property test (Hypothesis, run on Python 3.12 as before, `max_examples=25`, `deadline=None`): for random valid designs (points 4-11, replicates 1-8, factor 2-10 in steps of 0.5, transfer 5-100 µL with transfer x factor at most 300, controls 0-4 each), the simulator passes, `cost_model` equals the run-log count for tips and compound, and replaying the steps leaves every dilution well at `diluent_uL`.

### B1.2 Planner fixes

Problem. `plan_next_experiments` reruns candidates with `runs=500, seed=7` and the default `reader_cv`, while the baseline used the request's runs, seed and reader_cv. `drop_pct` therefore mixes Monte Carlo noise and a different reader setting into the comparison. Candidates can also break plate limits (10 points plus 2 makes 12, which no longer fits beside the control column).

Change:
- `plan_next_experiments(design, baseline, runs, seed, reader_cv)` uses the baseline's runs, seed and reader_cv for every candidate. Same seed means common random numbers, so the difference reflects the design, not the dice.
- Skip candidates that violate B1.1 limits.
- Extra cost = `cost_model(candidate) - cost_model(design)`.
- NextExperiment: add `design: ExperimentDesign | None = None` (the candidate) and `p90_after: float | None = None`.

Test. Same inputs twice give identical rankings. With `reader_cv=0.2`, every candidate report has reader_cv 0.2.

### B1.3 Samples and a curve band for the charts

Change. UncertaintyReport: add
- `samples: {true_ic50_nM: list[float], recovered_ic50_nM: list[float], fold_error: list[float]} | None = None` for the first `min(runs, 300)` runs.
- `curve: {concentrations_nM: list[float], activity_p10: list[float], activity_p50: list[float], activity_p90: list[float]} | None = None`: per nominal concentration, percentiles over all runs of the observed % activity (`y_obs`).

`_simulate_once` already computes `true_ic50` and `y_obs`. Return them.

Test. Lengths match. `fold_error[i] == max(r / t, t / r)` for each sample.

### B1.4 GET /api/protocol/{name}

Return the generated Python file as text/plain. `name` is the file's basename without `.py` and must match `^[A-Za-z0-9_-]{1,64}$`. Look in protocols/ then protocols/whatif/. 404 if missing.

### B1.5 Compute the four fixed axes

Each with its Source and a one-line `axis_notes` entry:
- novelty = share of reference topics with more works in 2020-2024 than this topic. Reference = the training topics in `topic_features`, counts from the cached works_by_year responses. Source openalex, id `reference: N topics`. If the cache lacks them, keep `assumed`.
- evidence = min(1, n_papers / 20), where n_papers is the chosen pair's count of independent ChEMBL papers. Note "20 or more independent papers counts as full evidence (our threshold)". Source chembl_activity.
- automatable = 1.0 if the stage 3 simulator passed, else 0.0. Source simulator.
- cost_time = 1 - min(1, tips / 96), the share of one tip rack left unused. Source simulator.

evidence, automatable and cost_time need stages 2 and 3, so recompute the matrix at the end of the orchestrator and save the topic report again (same weights, total from `ViabilityMatrix.weighted_total`).

### B1.6 Fill Source.url everywhere

| Source | URL |
|---|---|
| OpenAlex yearly counts | `https://api.openalex.org/works?filter=topics.id:{id},from_publication_date:2015-01-01,to_publication_date:2024-12-31&group_by=publication_year` (the exact query `works_by_year` makes) |
| OpenAlex topic | `https://api.openalex.org/topics/{id}` |
| ChEMBL activity | `https://www.ebi.ac.uk/chembl/api/data/activity/{activity_id}.json` |
| ChEMBL document | `https://www.ebi.ac.uk/chembl/api/data/document/{document_chembl_id}.json` |
| PubMed | `https://pubmed.ncbi.nlm.nih.gov/{pmid}/` |
| Paper | `https://doi.org/{doi}` |
| Opentrons spec | `https://docs.opentrons.com/flex/system-description/pipettes/` |

RationaleItem: add `url: str | None = None` and `document_chembl_id: str | None = None` (look up the document for chembl_activity items from the pair's papers).

## B2. Only after B0 and B1

### B2.1 Async run with live stage progress

POST /api/run with `"mode": "async"` (new RunRequest field, default `"sync"`) returns `{run_id, status: "started"}` at once and runs `run_pipeline` in a background thread. The orchestrator already saves each report and calls `set_run_status` after each stage. GET /api/run/{run_id} returns whatever is saved so far. On exception, set status `"error"` and store the message (add `runs.error TEXT` with the existing `_migrate` pattern). The DB handle is one shared sqlite3 connection with `check_same_thread=False`, so guard writes with a `threading.Lock`.

### B2.2 Real neighbors: "shift to a less explored topic"

For the resolved topic, read its subfield from the search hit, list sibling topics in that subfield (`https://api.openalex.org/topics?filter=subfield.id:{id}&per-page=50`, cached), keep siblings with fewer works in 2020-2024 than the query topic, fetch their counts with `works_by_year` (cached), score them with the momentum model, and return the top 5 by `p_growth` as Neighbor items. Add `RunRequest.openalex_topic_id: str | None = None` to run a chosen topic directly without search.

### B2.3 GET /api/metrics

Serve a JSON file written by the training and eval scripts (models/metrics.json): momentum AUROC with its spread and the slope baseline, top-10% precision, calibration coverage and pair count, simulator pass rate, citation error rate. One short description per metric. No recomputation per request.

### B2.4 GET /api/evidence/{compound_chembl_id}

Return that compound's entries from data/demo/evidence.json as `[{pmid, title, abstract, year, journal, document_chembl_id}]`. The dashboard highlights verified quotes inside the abstracts.

### B2.5 Skeptic turn: the LLM debate, settled by simulation

After the checker, ask Gemini (google-genai, `response_mime_type="application/json"`, `response_json_schema` from a Pydantic model, validate with `model_validate_json`) for at most 3 objections to the design, each `{field, proposed_value, argument}` with `field` in `dilution.top_nM, dilution.factor, dilution.points, replicates, volumes_uL.transfer`. Clamp proposals to B1.1 limits. Run each modified design through the uncertainty engine with the baseline seed and runs.

ExperimentDesign: add `review: list[ReviewTurn] = []` with `ReviewTurn {role: "skeptic", argument: str, field: str, proposed_value: float, p90_before: float, p90_after: float, extra_tips: int, extra_compound_uL: float, verdict: Literal["supported", "not supported"]}`. Verdict is "supported" when p90 drops by at least 5%. The argument is model text and is never verified. The design never changes because of a model's argument. Without GEMINI_API_KEY, skip and leave `review` empty.
