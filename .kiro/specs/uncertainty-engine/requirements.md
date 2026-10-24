# Uncertainty engine — requirements

The core ML piece. Answers: how far can a design's result land from the truth, and
which change tightens it most per unit of cost?

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

## Acceptance
- `run_uncertainty(design, runs=1000, seed=42)` returns a valid `UncertaintyReport` in < 1s.
- Same seed => identical p90 (covered by `tests/test_pipeline.py`).
- `coverage_90` on synthetic lognormal groups lands near 0.90.
