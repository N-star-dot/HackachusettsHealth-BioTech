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

## Calibration — what shipped (real ChEMBL data)

`scripts/build_calibration_data.py` pulls IC50 activities for a diverse set of well-studied
targets (EGFR, VEGFR2, hERG, HER2, CDK2, JAK2, mu-opioid, D2, PI3Kα; COX returned none in
the standard units), groups them by (target, compound), and stores every pair with >=3
measurements in the `calibration_groups` table. Current pull: **698 real pairs**, every
ChEMBL page cached so it runs offline.

The leave-one-out calibration check (`coverage_90`) then reports, against real held-out
measurements:

| | coverage_90 | spread (log10) |
|---|-------------|----------------|
| Default noise model | **0.85** | 0.68 (Kalliokoski 2013) |
| After auto-widening to target | **0.918** | 0.91 |

Honest read, reported both ways: the default model is slightly optimistic (covers 85% of
real held-out IC50s); `widen_until_calibrated` detects this and raises the assumed spread to
0.91 to reach the 90% target. Every `UncertaintyReport` now carries this real coverage in its
`calibration` field (was previously hardcoded to 0.0 — fixed).

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

