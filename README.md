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

## Quick start

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

# 6. API for the dashboard
uvicorn backend.api:app --reload      # http://127.0.0.1:8000/docs
```

The real Opentrons simulator is optional (it pins Python ≤ 3.13). Install it with
`pip install -e ".[robot]"` in a 3.13 environment; without it, stage 3 falls back to a
static protocol check so everything still runs.

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
frontend/    dashboard (owner C)
mocks/       one sample JSON per contract — build against these, never wait
scripts/     demo.py, eval_metrics.py, init_db.py
protocols/   generated Opentrons .py files
tests/       smoke + mock-validation tests
.kiro/       steering + specs (requirements/design per stage)   # committed, never gitignored
```

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
