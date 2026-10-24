"""Evaluation metrics reported in the README, video and slides.

Each metric is produced by a function here so the numbers are reproducible. Stubs are
clearly marked; wire them to real data as the ingest + model land.

    python scripts/eval_metrics.py
"""

from __future__ import annotations

import numpy as np

from backend.stage2_design import citation_error_rate, design_experiment
from backend.stage3_protocol import compile_design, simulate_protocol
from backend.stage4_uncertainty import coverage_90, run_uncertainty


def design_fold_error() -> dict:
    """Metric: 90th-percentile fold error of the reference design over 1000 runs."""
    design = design_experiment("T00000")
    rep = run_uncertainty(design, runs=1000, seed=42)
    return {"p90_fold_error": round(rep.fold_error.p90, 3),
            "median_fold_error": round(rep.fold_error.median, 3)}


def calibration_coverage() -> dict:
    """Metric: calibration coverage against REAL ChEMBL IC50 measurement groups.

    Reports coverage at the PUBLISHED spread (0.68) with no widening, plus the pooled
    within-group SD. Pulls groups from calibration_groups (one value per paper, >=3 papers).
    Falls back to synthetic groups only if the table is empty, clearly labelled.
    """
    from backend.stage4_uncertainty import pooled_within_group_sd
    from database import get_db

    rows = get_db().all_calibration_groups()
    real_groups = [r["values_nM"] for r in rows if len(r["values_nM"]) >= 3]

    if real_groups:
        cal = coverage_90(real_groups, spread_log10=0.68)
        pooled = pooled_within_group_sd(real_groups)
        return {
            "coverage_at_0.68": cal.coverage_90,
            "pooled_within_group_sd": round(pooled, 3),
            "pairs": cal.pairs,
            "data": "real ChEMBL (assay B, wild-type, paper-collapsed)",
        }

    rng = np.random.default_rng(0)
    groups = [list(10 ** rng.normal(2.0, 0.68, size=5)) for _ in range(200)]
    cal = coverage_90(groups, spread_log10=0.68)
    return {"coverage_at_0.68": cal.coverage_90, "pairs": cal.pairs,
            "data": "SYNTHETIC (run build_calibration_data.py)"}


def simulator_pass_rate() -> dict:
    """Metric: share of compiled designs that pass the Opentrons simulator."""
    design = design_experiment("T00000")
    path = compile_design(design)
    sim = simulate_protocol(path, design)
    return {"pass_rate": 1.0 if sim.simulator.passed else 0.0,
            "note": sim.simulator.opentrons_version}


def citation_error() -> dict:
    """Metric: citation error rate before checking (offline => all unverified)."""
    design = design_experiment("T00000")
    return {"citation_error_rate_before_check": round(citation_error_rate(design), 3)}


def main() -> int:
    print("=== Evaluation metrics ===")
    for name, fn in [
        ("Design fold error", design_fold_error),
        ("Calibration coverage", calibration_coverage),
        ("Simulator pass rate", simulator_pass_rate),
        ("Citation error rate", citation_error),
    ]:
        print(f"\n[{name}]")
        for k, v in fn().items():
            print(f"  {k}: {v}")
    print("\n(Momentum AUROC vs slope baseline and the debate ablation are reported once"
          "\n the trained model and LLM designer land — see .kiro/specs.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
