# Uncertainty engine — design

## Files
- `engine.py` — `run_uncertainty(design, runs, seed, reader_cv) -> UncertaintyReport`.
- `noise_sources.py` — single source of truth for every noise level + `lookup_pipette_error`.
- `calibration.py` — `coverage_90(groups)`, `widen_until_calibrated(groups)`.
- `planner.py` — `plan_next_experiments(design, baseline)`.

## One Monte Carlo run (`_simulate_once`)
1. Draw a true IC50: `log10(prior_median) + N(0, lab_spread_log10)`.
2. Realise concentrations: `concentrations * bias * cumprod(jitter)` where `bias ~ 1 + N(0, pipette_bias)`
   applied to the whole series (direction persists) and `jitter ~ N(1, pipette_cv)` per well
   (so random scatter compounds along the chain).
3. Readout: Hill curve + reader scatter, averaged over `replicates`.
4. Fit the Hill curve with `scipy.optimize.curve_fit` (bounded); record recovered IC50 and
   whether the fit failed.

Vectorised with numpy; the per-run loop is cheap enough for 1,000 runs per slider move.

## Pipetting spec table
`noise_sources._PIPETTE_SPEC` keyed by pipette family -> ascending (min_volume, random_cv, bias).
`lookup_pipette_error` picks the band for the design's transfer volume. The 1 µL regime
(7% random / 8% bias) is deliberately costly so the planner avoids it.

## Planner scoring
`score = p90_fold_error_drop_pct / cost_units`, where
`cost_units = extra_tips + extra_compound_uL/10 + extra_plates*50`. Ranked descending.

## Calibration
Leave-one-out over each group; 90% interval = mean(rest) ± 1.645 * spread (log10 space).
`widen_until_calibrated` multiplies spread by 1.1 until coverage >= target, returns before/after.

## Related work note (for the pitch)
Choosing experiments by expected information is the same idea behind Bayesian optimization,
which beat human chemists on efficiency/bias in a Princeton + BMS study (Nature, 2021).
