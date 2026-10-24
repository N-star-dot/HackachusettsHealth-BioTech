"""Next-experiment planner. Owner A.

Proposes candidate design changes, reruns the Monte Carlo for each with the SAME runs,
seed and reader_cv as the baseline (common random numbers, so a p90 difference reflects
the design change and not Monte Carlo noise), and ranks them by fold-error reduction per
unit of cost. Candidates that break the B1.1 plate/volume limits are skipped. Extra cost
comes from cost_model, so it matches what the robot would actually use.
"""

from __future__ import annotations

import copy

from backend.contracts import ExperimentDesign, NextExperiment, UncertaintyReport
from backend.stage3_protocol import cost_model
from backend.stage4_uncertainty.engine import run_uncertainty

_MAX_POINTS = 11
_MAX_REPLICATES = 8
_MAX_CONTROL_WELLS = 8
_WELLS = 96


def _valid(design: ExperimentDesign) -> bool:
    """Does the design satisfy the B1.1 plate/volume limits?"""
    d = design
    if not (2 <= d.dilution.points <= _MAX_POINTS):
        return False
    if not (1 <= d.replicates <= _MAX_REPLICATES):
        return False
    if d.controls.positive_wells + d.controls.negative_wells > _MAX_CONTROL_WELLS:
        return False
    if d.dilution.points * d.replicates + d.controls.positive_wells + d.controls.negative_wells > _WELLS:
        return False
    if d.volumes_uL.transfer * d.dilution.factor > 300.0 + 1e-6:
        return False
    if d.volumes_uL.transfer < 5.0:  # the 1000 µL pipette minimum
        return False
    return True


def _rebuild_volumes(d: ExperimentDesign) -> None:
    """Keep diluent consistent with the (possibly changed) factor, in place."""
    d.volumes_uL.diluent = d.volumes_uL.transfer * (d.dilution.factor - 1.0)


def _candidates(design: ExperimentDesign) -> list[tuple[str, ExperimentDesign]]:
    """Return (label, candidate) pairs that satisfy the B1.1 limits."""
    out: list[tuple[str, ExperimentDesign]] = []

    def add(label: str, mutate) -> None:
        d = copy.deepcopy(design)
        mutate(d)
        _rebuild_volumes(d)
        try:
            d = ExperimentDesign.model_validate(d.model_dump())  # re-run validators
        except Exception:
            return
        if _valid(d):
            out.append((label, d))

    add(f"add 1 replicate ({design.replicates + 1} total)",
        lambda d: setattr(d, "replicates", d.replicates + 1))
    add("add 2 dilution points",
        lambda d: setattr(d.dilution, "points", d.dilution.points + 2))
    add(f"tighten dilution factor to {max(2.0, design.dilution.factor - 1.0):g}",
        lambda d: setattr(d.dilution, "factor", max(2.0, d.dilution.factor - 1.0)))
    if design.volumes_uL.transfer < 5.0:
        add("raise transfer volume to 5 µL",
            lambda d: setattr(d.volumes_uL, "transfer", 5.0))

    return out


def plan_next_experiments(
    design: ExperimentDesign,
    baseline: UncertaintyReport,
    runs: int | None = None,
    seed: int | None = None,
    reader_cv: float | None = None,
    top_k: int = 3,
) -> list[NextExperiment]:
    # use the baseline's own settings so the comparison is apples-to-apples
    runs = runs if runs is not None else baseline.runs
    seed = seed if seed is not None else baseline.seed
    reader_cv = reader_cv if reader_cv is not None else baseline.noise.reader_cv

    base_p90 = baseline.fold_error.p90
    base_cost = cost_model(design)
    ranked: list[NextExperiment] = []

    for label, cand in _candidates(design):
        rep = run_uncertainty(cand, runs=runs, seed=seed, reader_cv=reader_cv,
                              calibrate_coverage=False)
        drop_pct = max(0.0, (base_p90 - rep.fold_error.p90) / max(base_p90 - 1.0, 1e-6) * 100.0)

        cand_cost = cost_model(cand)
        extra_tips = max(0, cand_cost["tips"] - base_cost["tips"])
        extra_compound = max(0.0, cand_cost["compound_uL"] - base_cost["compound_uL"])
        extra_plates = max(0, cand_cost["plates"] - base_cost["plates"])
        cost_units = extra_tips + extra_compound / 10.0 + extra_plates * 50.0
        score = drop_pct / cost_units if cost_units > 0 else drop_pct

        ranked.append(NextExperiment(
            change=label,
            p90_fold_error_drop_pct=round(drop_pct, 1),
            extra_tips=extra_tips,
            extra_compound_uL=round(extra_compound, 2),
            extra_plates=extra_plates,
            score=round(score, 3),
            design=cand,
            p90_after=round(rep.fold_error.p90, 4),
        ))

    ranked.sort(key=lambda x: x.score, reverse=True)
    return ranked[:top_k]
