"""Calibration: is our uncertainty honest against real data? Owner A.

Takes compound-target pairs with >=3 ChEMBL IC50 values, holds one out, predicts a
90% range from the rest (our lab-spread model), and counts how often the held-out
value lands inside. Coverage near 0.90 means the noise model is calibrated; lower
means too optimistic, so we widen it and report before/after.

This module works on already-pulled ChEMBL measurement groups (provided by the
pipeline/ingest workstream) so it has no network dependency itself.
"""

from __future__ import annotations

import math

import numpy as np

from backend.contracts import Calibration
from backend.stage4_uncertainty.noise_sources import LAB_SPREAD_LOG10


def coverage_90(groups: list[list[float]], spread_log10: float = LAB_SPREAD_LOG10) -> Calibration:
    """`groups` is a list of per-pair IC50 value lists (nM), each with >=3 values
    (one per paper).

    For each group we leave one value out and ask whether the held-out paper's value falls
    in a 90% prediction interval built from the remaining m values. The interval is centred
    on the mean of the rest, with half-width:

        1.645 * spread * sqrt(1 + 1/m)

    The sqrt(1 + 1/m) term accounts for the fact that the centre (the mean of m values) is
    itself uncertain — omitting it makes the interval too narrow and understates coverage.
    No widening: we report coverage at the published spread as-is.
    """
    z = 1.645  # 90% two-sided normal quantile
    hits = 0
    total = 0
    for values in groups:
        if len(values) < 3:
            continue
        logs = np.log10(np.array(values, dtype=float))
        for i in range(len(logs)):
            held = logs[i]
            rest = np.delete(logs, i)
            m = len(rest)
            center = rest.mean()
            half = z * spread_log10 * math.sqrt(1.0 + 1.0 / m)
            lo, hi = center - half, center + half
            hits += int(lo <= held <= hi)
            total += 1
    cov = hits / total if total else 0.0
    return Calibration(coverage_90=round(cov, 3), pairs=len([g for g in groups if len(g) >= 3]))


def pooled_within_group_sd(groups: list[list[float]]) -> float:
    """Pooled within-group SD in log10 units across all groups at once.

    sqrt( sum over groups of sum (x - group_mean)^2  /  sum over groups of (n - 1) ).
    This is the honest measure of how much papers disagree; per-group SDs averaged over
    small groups look artificially tight.
    """
    ss = 0.0
    dof = 0
    for values in groups:
        if len(values) < 2:
            continue
        logs = np.log10(np.array(values, dtype=float))
        mean = logs.mean()
        ss += float(((logs - mean) ** 2).sum())
        dof += len(logs) - 1
    return math.sqrt(ss / dof) if dof > 0 else 0.0


def widen_until_calibrated(
    groups: list[list[float]], target: float = 0.90, start: float = LAB_SPREAD_LOG10
) -> tuple[float, Calibration, Calibration]:
    """If coverage is below target, widen the spread until it meets target.
    Returns (final_spread, before, after)."""
    before = coverage_90(groups, start)
    spread = start
    after = before
    for _ in range(20):
        if after.coverage_90 >= target:
            break
        spread *= 1.1
        after = coverage_90(groups, spread)
    return spread, before, after


def load_calibration_groups() -> list[list[float]]:
    """Load real ChEMBL IC50 measurement groups from the database.

    Returns a list of per-pair value lists (nM), each with >=3 values. Empty if the
    calibration_groups table hasn't been populated (run build_calibration_data.py).
    Import of the DB is local so engine.py has no hard DB dependency when groups are
    passed in directly.
    """
    try:
        from database import get_db

        rows = get_db().all_calibration_groups()
        return [r["values_nM"] for r in rows if len(r["values_nM"]) >= 3]
    except Exception:
        return []


def calibrate(spread_log10: float, groups: list[list[float]] | None = None) -> Calibration:
    """Coverage of the given noise spread against real ChEMBL groups (loaded from the DB
    if not supplied). Returns a zeroed Calibration if no groups are available."""
    if groups is None:
        groups = load_calibration_groups()
    if not groups:
        return Calibration(coverage_90=0.0, pairs=0)
    return coverage_90(groups, spread_log10)
