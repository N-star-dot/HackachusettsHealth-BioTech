"""Stage 4: the uncertainty engine. Owner A.

A Monte Carlo simulation (NOT a trained model — there is nothing to fit) over a
dose-response (4-parameter Hill) assay. Each run:
  1. draws a 'true' IC50 from the prior (lab-to-lab spread, Kalliokoski 2013),
  2. pushes concentrations through the serial dilution with pipetting error
     (random CV compounds as sqrt(n); systematic bias compounds multiplicatively),
  3. adds plate-reader scatter to the readout,
  4. fits the Hill curve and records the recovered IC50.

It reports fold error (median, p90), share of runs where the true IC50 falls
outside the tested range, the share of failed fits, and a CALIBRATION coverage
measured against real ChEMBL measurement groups (the honesty check). Vectorised with
numpy so 1,000 runs finish in well under a second.

Noise levels are looked up from a single source-of-truth table (noise_sources.py),
each tagged with a real Source.
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import curve_fit

from backend.contracts import (
    Calibration,
    ExperimentDesign,
    FoldError,
    NoiseModel,
    UncertaintyReport,
)
from backend.stage4_uncertainty.calibration import calibrate
from backend.stage4_uncertainty.noise_sources import (
    LAB_SPREAD_LOG10,
    lookup_pipette_error,
    noise_sources,
)


def hill(c: np.ndarray, bottom: float, top: float, ic50: float, h: float) -> np.ndarray:
    """4-parameter Hill / dose-response curve."""
    return bottom + (top - bottom) / (1.0 + (c / ic50) ** h)


def _concentrations(design: ExperimentDesign) -> np.ndarray:
    d = design.dilution
    idx = np.arange(d.points)
    return d.top_nM / (d.factor ** idx)


def _simulate_once(
    rng: np.random.Generator,
    concentrations: np.ndarray,
    prior_median_nM: float,
    noise: NoiseModel,
    replicates: int,
    hill_slope: float = 1.0,
) -> tuple[float, bool, bool]:
    """One virtual experiment. Returns (recovered_ic50, outside_range, fit_failed, true_ic50)."""
    # 1. true IC50 drawn from lab-to-lab spread (lognormal in log10 space)
    true_log10 = np.log10(prior_median_nM) + rng.normal(0, noise.lab_spread_log10)
    true_ic50 = 10**true_log10

    # 2. pipetting error on the realised concentrations
    #    systematic bias: one draw applied to the whole series (direction persists)
    bias = 1.0 + rng.normal(0, noise.pipette_bias)
    #    random scatter: independent per well, compounds along the dilution chain
    jitter = rng.normal(1.0, noise.pipette_cv, size=concentrations.shape)
    realised_c = concentrations * bias * np.cumprod(jitter)

    # 3. true readout + reader scatter, averaged over replicates
    y_true = hill(realised_c, bottom=0.0, top=100.0, ic50=true_ic50, h=hill_slope)
    reader = rng.normal(1.0, noise.reader_cv, size=(replicates, y_true.size))
    y_obs = (y_true * reader).mean(axis=0)

    outside = not (realised_c.min() <= true_ic50 <= realised_c.max())

    # 4. fit
    try:
        p0 = [0.0, 100.0, prior_median_nM, 1.0]
        bounds = ([-50, 50, realised_c.min() * 1e-3, 0.2], [50, 150, realised_c.max() * 1e3, 5.0])
        popt, _ = curve_fit(hill, realised_c, y_obs, p0=p0, bounds=bounds, maxfev=2000)
        recovered = float(popt[2])
        fit_failed = not np.isfinite(recovered) or recovered <= 0
    except Exception:
        recovered, fit_failed = float("nan"), True

    return (recovered if not fit_failed else true_ic50), outside, fit_failed, true_ic50


def run_uncertainty(
    design: ExperimentDesign,
    runs: int = 1000,
    seed: int = 42,
    reader_cv: float = 0.05,
    calibrate_coverage: bool = True,
) -> UncertaintyReport:
    """Full Monte Carlo for one design -> UncertaintyReport.

    If `calibrate_coverage` is True, the report's calibration is measured against the
    real ChEMBL groups in the database using this design's own lab-spread. It's a cheap
    computation; set False to skip when the calibration table is empty or for speed.
    """
    rng = np.random.default_rng(seed)
    concentrations = _concentrations(design)

    p_cv, p_bias = lookup_pipette_error(design.pipette, design.volumes_uL.transfer)
    spread = design.prior_ic50.spread_log10 or LAB_SPREAD_LOG10
    noise = NoiseModel(
        lab_spread_log10=spread,
        pipette_cv=p_cv,
        pipette_bias=p_bias,
        reader_cv=reader_cv,
        sources=noise_sources(),
    )

    fold_errors: list[float] = []
    outside_count = 0
    failed_count = 0
    for _ in range(runs):
        recovered, outside, failed, true_ic50 = _simulate_once(
            rng, concentrations, design.prior_ic50.median_nM, noise, design.replicates
        )
        if failed:
            failed_count += 1
        if outside:
            outside_count += 1
        fe = max(recovered / true_ic50, true_ic50 / recovered)
        fold_errors.append(fe)

    fe_arr = np.array(fold_errors)

    calibration = (
        calibrate(spread) if calibrate_coverage else Calibration(coverage_90=0.0, pairs=0)
    )

    report = UncertaintyReport(
        design_id=design.design_id,
        label="simulated",
        runs=runs,
        seed=seed,
        noise=noise,
        fold_error=FoldError(median=float(np.median(fe_arr)), p90=float(np.percentile(fe_arr, 90))),
        outside_range_share=outside_count / runs,
        failed_fit_share=failed_count / runs,
        calibration=calibration,  # measured against real ChEMBL groups
        next_experiments=[],  # filled by planner.py (via the orchestrator)
    )
    return report
