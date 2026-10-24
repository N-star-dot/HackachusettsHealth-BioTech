# HackachusettsHealth-BioTech

**Track: Healthcare & Biotech**

A researcher types a topic and gets three things back:

1. **Where the open questions are** — momentum and novelty scored from real publication data.
2. **A ready-to-run robot protocol** — a dose-response experiment compiled for the Opentrons
   Flex liquid-handling robot and checked by the Opentrons simulator.
3. **An honest estimate of real-world noise** — a Monte Carlo engine that reruns the virtual
   experiment ~1,000 times with noise taken from real measurements, and ranks the next
   experiment by uncertainty removed per unit of cost.

It is for student researchers, early-stage labs, and young biotech companies in Massachusetts
that pick experiments without a data science team.

> We don't claim to be first. Related work: Google's co-scientist, and CMU's Coscientist
> (2023). Our edge is that we're **free, open, student-scale, every number traces to a source,
> and the simulation checks its own uncertainty against real data.**

---

## Quick start (command line, offline)

```bash
# 1. setup (Python 3.10+)
python -m pip install --upgrade pip
pip install -e ".[dev]"

# 2. create the local database and load the offline cache seed
python scripts/init_db.py

# 3. run the whole pipeline end-to-end, offline
INGEST_OFFLINE=1 python scripts/demo.py "kinase inhibitors for liver fibrosis"

# 4. the reported evaluation metrics
python scripts/eval_metrics.py

# 5. tests
python -m pytest -q
```

---

## Run the full app (dashboard + API)

The dashboard is two processes: the **FastAPI backend** and the **Vite dev server** for the
frontend. Run each in its own terminal.

### Prerequisites
- Python 3.10–3.13 and Node 18+ (`node -v`).
- For the **real robot simulation**, the Opentrons package must be installed. It pins
  Python ≤ 3.13, so it lives in a separate environment (see below). Without it, stage 3
  still runs but reports a static protocol check (no animated replay, no step-by-step log).

### 1. Backend — use the environment that has Opentrons

If you installed Opentrons into a dedicated env (recommended), start the server from it.
A ready-made script does this and, importantly, keeps `uvicorn --reload` from restarting
mid-run (the pipeline writes generated files during a run):

```bash
./scripts/serve.sh
```

That runs, in effect:

```bash
# from the env that has opentrons installed
<python-with-opentrons> -m uvicorn backend.api:app --reload \
  --reload-dir backend --reload-dir pipeline \
  --host 127.0.0.1 --port 8000
```

Set `LABPLANNER_PYTHON` to point the script at your Opentrons env's interpreter, e.g.:

```bash
LABPLANNER_PYTHON=/path/to/opentrons-env/bin/python ./scripts/serve.sh
```

If you don't need the real simulator, plain `uvicorn backend.api:app --reload` works too —
generated protocol files are written outside the repo tree, so a run won't trigger a reload.

API docs: http://127.0.0.1:8000/docs. Health check: http://127.0.0.1:8000/api/health.

**Installing the Opentrons env (one time):**
```bash
# any Python <=3.13 environment (conda, venv, etc.)
python3.12 -m venv .venv-robot && source .venv-robot/bin/activate
pip install --upgrade pip && pip install -e ".[dev,robot]"
python scripts/init_db.py
# (optional) retrain the momentum model in THIS env so the pickle loads cleanly:
python scripts/train_momentum.py
```
The trained model (`models/momentum_hgb.pkl`) is gitignored and not portable across
numpy/scikit-learn versions. `load_model()` falls back to a slope heuristic with a warning
if the pickle was written by a different env, so the pipeline never crashes.

### 2. Frontend — Vite dev server

```bash
cd frontend
npm install
npm run dev            # http://localhost:5173
```

The dev server proxies `/api/*` to `http://127.0.0.1:8000`, so start the backend first.

### 3. Use it
Open http://localhost:5173, type a research topic (or click an example such as
"HER2 kinase inhibitors in breast cancer"), and press Run. The first run of a topic pulls
from OpenAlex/ChEMBL and caches the responses; later runs are fast and work offline.

**Offline / no-backend demo:** the frontend ships three recorded runs. Open
`http://localhost:5173/?demo=run-1.json` (or `run-2.json`, `run-3.json`) to replay a real
run with no backend running — useful for a reliable demo.

### Typical two-terminal session
```bash
# terminal 1 — backend (with Opentrons)
./scripts/serve.sh

# terminal 2 — frontend
cd frontend && npm run dev
```

### Frontend checks
```bash
cd frontend
npm run typecheck      # tsc, no emit
npm run build          # production build
npm test               # vitest
```

### LLM design debate (optional)
Stage 2's skeptic debate uses Google Gemini. Without a key it is skipped and the review
shows only the deterministic designer, the citation checker, and the rule checks (no fake
debate). To enable it, add to `.env`:
```
GEMINI_API_KEY=your-key-from-https://aistudio.google.com/apikey
LLM_MODEL=gemini-2.5-flash
```
then restart the backend.

### Troubleshooting
- **"Static check only. Not simulated."** on the robot step → the backend is running in an
  env without Opentrons. Start it from the Opentrons env (see `scripts/serve.sh`).
- **A run that never finishes** → make sure the backend was started with `scripts/serve.sh`
  (or plain `uvicorn`); older ad-hoc `--reload` invocations that watch the whole repo can
  restart the server mid-run.
- **Topic shows "unavailable offline"** → OpenAlex could not be reached for that query;
  the experiment stages below don't depend on it.

### Running offline (cache seed)
External data (OpenAlex / PubMed / ChEMBL) is pulled once and cached, so the demo runs
with no network. `scripts/init_db.py` loads a committed cache seed from `database/seed/`
into the local DB, and `INGEST_OFFLINE=1` guarantees the pipeline never touches the
network — a cached request is served locally; an uncached one raises instead of fetching.

To refresh the seed with live data (run once, online, then commit the result):

```bash
python scripts/seed_cache.py --online --topic "kinase inhibitors for liver fibrosis"
```

API keys are optional (keyless works at lower rate limits). Copy `.env.example` to `.env`
and fill in any of `OPENALEX_API_KEY`, `NCBI_API_KEY`, `CONTACT_EMAIL` to raise limits;
`.env` is loaded automatically and is gitignored.

---

## How it works — five stages, four contracts

Each stage hands the next a JSON contract (`backend/contracts`), so the workstreams build in
parallel against `mocks/`.

| Stage | What happens | Output contract | Real or simulated |
|-------|--------------|-----------------|-------------------|
| 1 Topic scoring | Safety gate → momentum model → novelty gap → viability matrix | `TopicReport` | Real (OpenAlex/PubMed) |
| 2 Experiment design | Designer LLM writes JSON; every PMID verified | `ExperimentDesign` | Real (PubMed/ChEMBL) |
| 3 Protocol + check | Fixed template → Opentrons Flex program → simulator | `SimResult` | Real (Opentrons sim) |
| 4 Uncertainty engine | 1,000-run Monte Carlo + calibration + next-experiment planner | `UncertaintyReport` | **Simulated readouts**, real noise levels |
| 5 Dashboard | Matrix, what-if sliders, run replay, source-on-hover | live demo | — |

Only the stage-4 assay readouts are simulated. Every other number carries a source, shown on
hover in the dashboard. IC50 = the concentration at which a compound halves its target's
activity; lower means more potent, and it's the number our experiments estimate.

### The uncertainty engine (the core ML piece)
Each Monte Carlo run draws a true IC50 from the lab-to-lab spread (Kalliokoski 2013, 0.68
log10 units), pushes concentrations through the serial dilution with Opentrons pipetting error
(random scatter compounds as √n, systematic bias multiplicatively), adds plate-reader scatter,
fits the 4-parameter Hill curve, and records the recovered IC50. Biology dominates: the
~2.7-fold lab spread dwarfs robot error except at 1 µL transfers, which the planner avoids.
**Calibration** holds out real ChEMBL values and checks our 90% interval actually covers ~90%.

---

## Project layout

```
backend/     contracts/ safety/ stage1_topic/ stage2_design/ stage3_protocol/ stage4_uncertainty/ api/
pipeline/    ingest/ (cached OpenAlex/PubMed/ChEMBL clients) + orchestrator.py   # teammate-owned
database/    SQLite schema + access layer (api cache + runs + reports)
frontend/    React + TypeScript + Vite dashboard
mocks/       one sample JSON per contract — build against these, never wait
scripts/     demo.py, eval_metrics.py, init_db.py, serve.sh (dashboard API)
tests/       smoke + mock-validation tests
.kiro/       steering + specs (requirements/design per stage)   # committed, never gitignored
```

Generated Opentrons protocol `.py` files are written to a temp dir outside the repo
(override with `PROTOCOLS_DIR`), so a dev-server reload never fires mid-run.

Full structure, ownership (A/B/C + pipeline teammate), and the working agreement are in
`.kiro/steering/structure.md`.

---

## Reported metrics
Produced by `scripts/eval_metrics.py`:
- **Design fold error** — p90 fold error of a design over 1,000 runs.
- **Calibration coverage** — share of held-out ChEMBL values inside the 90% range (target ~0.90).
- **Simulator pass rate** — compiled designs that pass the Opentrons simulator.
- **Citation error rate** — PMIDs that don't resolve or mismatch, before/after checking.
- **Momentum AUROC vs slope baseline** and the **debate ablation** land with the trained model
  and the LLM designer (see `.kiro/specs`).

We report every number as it comes out, including weaknesses.

## Data sources
OpenAlex (topic counts/trends), PubMed/NCBI E-utilities (abstracts + PMID checks), ChEMBL
(IC50 measurements), Opentrons simulator + Flex pipette specs. Every response is cached on
first pull so the demo runs offline. We do **not** use Google Scholar (its robots.txt
disallows automated access).

## Built with Kiro
This project was built throughout with Kiro. The `.kiro/` folder (committed at the repo root)
holds the steering files that encode our product rules and tech conventions, and a spec
(requirements + design) for each stage.
