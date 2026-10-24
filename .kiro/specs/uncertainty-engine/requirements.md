# Uncertainty engine — requirements

A Monte Carlo SIMULATION (not a trained model — nothing to fit). Answers: how far can a
design's result land from the truth, and which change tightens it most per unit of cost?

## Requirements
1. **Monte Carlo over the Hill curve.** Rerun the virtual dose-response experiment ~1,000
   times with fresh noise; report fold error (median, p90), outside-range share, failed-fit share.
2. **Noise from named sources, kept separate.** Lab-to-lab IC50 spread (Kalliokoski 2013,
   0.68 log10), pipetting random CV + systematic bias (Opentrons Flex spec, per volume band),
   plate-reader CV (user-set, default 5%). Each tagged with a `Source`.
3. **Error compounding is modelled correctly.** Random scatter compounds as √n along the
   dilution chain; systematic bias compounds multiplicatively.
4. **Calibration against real data.** Hold out ChEMBL values from pairs with >=3 measurements,
   predict a 90% range, count coverage. Near 0.90 = honest. If low, widen and report before/after.
5. **Next-experiment planner.** Propose changes (shift range, add points, add replicates, change
   factor, raise transfer volume), rerun the sim for each, rank by p90-fold-error-drop per unit cost.
6. **Fast + deterministic.** 1,000 runs well under a second; identical results for a fixed seed.
7. **Separate epistemic from aleatoric.** Show the lab-to-lab floor separately so nobody pays to
   chase noise more replicates can't remove.

## Calibration — what shipped (real ChEMBL data, done correctly)

### Data (`scripts/build_calibration_data.py`)
Pulls IC50 activities for a diverse set of well-studied targets, keeping only:
  * records with a non-null `pchembl_value` (rejects censored '>'/'<' and quality-flagged),
  * `assay_type = B` (binding/biochemical on purified protein — exactly what the app
    simulates; cell-based 'F' assays give different numbers and inflate apparent disagreement),
  * wild-type target (empty `assay_variant_mutation`),
  * non-`potential_duplicate` records.

Each **source paper is collapsed to one value** (its median pChEMBL), so a single prolific
paper can't dominate, and a group must span **>= 3 distinct papers** — because the test asks
where a *new paper's* value would land, not one lab's repeatability.

### Math (`backend/stage4_uncertainty/calibration.py`)
Leave-one-paper-out. The 90% prediction interval half-width is

    1.645 * spread * sqrt(1 + 1/m)

where m = remaining papers. The `sqrt(1 + 1/m)` term accounts for the uncertainty in the
interval's own centre (the mean of m values); omitting it makes the interval too narrow and
understates coverage. **No widening** — we report coverage at the published spread as-is, so
this is a genuine test, not an error bar tuned to pass itself.

### Result (87 drug–target pairs)
| Metric | Value | Reference |
|--------|-------|-----------|
| Pooled within-group SD | **0.683 log10** | Kalliokoski 2013: 0.68 |
| Coverage at spread 0.68 (no widening) | **0.896** | target 0.90 |

Slide line: *"Across 87 drug–target pairs, labs disagree by 0.68 log units (published: 0.68),
and our 90% range catches 90% of held-out papers — with no widening."*

### Demo pairs (`scripts/build_demo_pairs.py` -> data/demo/demo_pairs.json)
Real approved/well-studied drugs on their intended targets, replacing the CHEMBL0000 /
fixed-120nM placeholders. Each prior is paper-collapsed (median across papers, SD ddof=1):
  * lapatinib on HER2 — 24 nM, spread 0.93, 21 papers
  * SB-203580 on p38α (MAPK14) — 65 nM, spread 0.80, 16 papers
  * tofacitinib on JAK2 — 11.5 nM, spread 0.84, 14 papers

Every `UncertaintyReport` carries real coverage in its `calibration` field.

## Acceptance
- `run_uncertainty(design, runs=1000, seed=42)` returns a valid `UncertaintyReport` in < 1s,
  with `calibration.pairs > 0` when the calibration table is populated.
- Same seed => identical p90 (covered by `tests/test_pipeline.py`).
- `coverage_90` lands near 0.90 on data whose spread matches the assumed spread; widening
  never lowers coverage (both covered by tests).

## Status
Engine complete: Monte Carlo + compounding noise + planner + **real-ChEMBL calibration wired
into the report**. Optional next step: broaden calibration beyond 9 targets and handle COX's
units convention.

