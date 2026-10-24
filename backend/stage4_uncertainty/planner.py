"""Next-experiment planner. Owner A.

Proposes candidate design changes, reruns the Monte Carlo for each, and ranks them by
fold-error reduction per unit of cost (tips, µL, plates). Dollars only appear when the
user supplies unit prices.
"""

from __future__ import annotations

import copy

from backend.contracts import ExperimentDesign, NextExperiment, UncertaintyReport
from backend.stage4_uncertainty.engine import run_uncertainty


def _candidates(design: ExperimentDesign) -> list[tuple[str, ExperimentDesign, dict]]:
    """Return (label, mutated_design, extra_cost) candidates."""
    out = []

    # add replicates
    d = copy.deepcopy(design)
    d.replicates += 1
    out.append((f"add 1 replicate ({d.replicates} total)", d,
                {"extra_tips": design.dilution.points, "extra_compound_uL": 0.0, "extra_plates": 0}))

    # add dilution points (widen low end)
    d = copy.deepcopy(design)
    d.dilution.points += 2
    out.append(("add 2 dilution points", d,
                {"extra_tips": 2, "extra_compound_uL": 0.0, "extra_plates": 0}))

    # finer dilution factor (more resolution near IC50)
    d = copy.deepcopy(design)
    d.dilution.factor = max(2.0, design.dilution.factor - 1.0)
    out.append((f"tighten dilution factor to {d.dilution.factor:g}", d,
                {"extra_tips": 0, "extra_compound_uL": 0.0, "extra_plates": 0}))

    # raise transfer volume above the noisy <5µL regime
    if design.volumes_uL.transfer < 5.0:
        d = copy.deepcopy(design)
        d.volumes_uL.transfer = 5.0
        out.append(("raise transfer volume to 5 µL", d,
                    {"extra_tips": 0, "extra_compound_uL": design.dilution.points * 4.0, "extra_plates": 0}))

    return out


def plan_next_experiments(
    design: ExperimentDesign,
    baseline: UncertaintyReport,
    runs: int = 500,
    seed: int = 7,
    top_k: int = 3,
) -> list[NextExperiment]:
    base_p90 = baseline.fold_error.p90
    ranked: list[NextExperiment] = []

    for label, cand, cost in _candidates(design):
        rep = run_uncertainty(cand, runs=runs, seed=seed)
        drop_pct = max(0.0, (base_p90 - rep.fold_error.p90) / max(base_p90 - 1.0, 1e-6) * 100.0)
        cost_units = cost["extra_tips"] + cost["extra_compound_uL"] / 10.0 + cost["extra_plates"] * 50.0
        score = drop_pct / cost_units if cost_units > 0 else drop_pct
        ranked.append(
            NextExperiment(
                change=label,
                p90_fold_error_drop_pct=round(drop_pct, 1),
                extra_tips=cost["extra_tips"],
                extra_compound_uL=cost["extra_compound_uL"],
                extra_plates=cost["extra_plates"],
                score=round(score, 3),
            )
        )

    ranked.sort(key=lambda x: x.score, reverse=True)
    return ranked[:top_k]
