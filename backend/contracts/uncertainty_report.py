"""UncertaintyReport (stage 4 output).

A's Monte Carlo engine produces this; C shows it. The whole block is labelled
`simulated` because the assay readouts are synthetic — but every NOISE LEVEL inside
still traces to a real source.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from backend.contracts.common import Source


class NoiseModel(BaseModel):
    lab_spread_log10: float = Field(..., ge=0, description="Kalliokoski 2013 lab-to-lab IC50 spread.")
    pipette_cv: float = Field(..., ge=0, description="Random pipetting scatter (coefficient of variation).")
    pipette_bias: float = Field(..., ge=0, description="Systematic pipetting bias.")
    reader_cv: float = Field(..., ge=0, description="Plate-reader scatter, user-set, default 0.05.")
    sources: list[Source] = Field(default_factory=list)


class FoldError(BaseModel):
    median: float = Field(..., ge=1.0)
    p90: float = Field(..., ge=1.0, description="90th percentile fold error.")


class Calibration(BaseModel):
    """Honest check of the noise model against held-out real ChEMBL values.
    coverage_90 near 0.90 means the uncertainty is calibrated."""

    coverage_90: float = Field(..., ge=0.0, le=1.0)
    pairs: int = Field(..., ge=0)


class NextExperiment(BaseModel):
    change: str
    p90_fold_error_drop_pct: float = Field(..., description="Expected reduction in p90 fold error, percent.")
    extra_tips: int = Field(default=0)
    extra_compound_uL: float = Field(default=0.0)
    extra_plates: int = Field(default=0)
    score: float = Field(..., description="Fold-error reduction per unit cost. Higher ranks first.")


class UncertaintyReport(BaseModel):
    design_id: str
    label: str = Field(default="simulated", description="Always 'simulated' — the readouts are synthetic.")
    runs: int = Field(..., ge=1)
    seed: int
    noise: NoiseModel
    fold_error: FoldError
    outside_range_share: float = Field(..., ge=0.0, le=1.0)
    failed_fit_share: float = Field(..., ge=0.0, le=1.0)
    calibration: Calibration
    next_experiments: list[NextExperiment] = Field(default_factory=list)
