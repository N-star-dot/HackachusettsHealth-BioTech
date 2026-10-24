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
    """`groups` is a list of per-pair IC50 value lists (nM), each with >=3 values.

    For each group we leave one out, build a 90% interval around the mean of the rest
    (± 1.645 * spread in log10 space), and check containment of the held-out value.
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
            center = rest.mean()
            lo, hi = center - z * spread_log10, center + z * spread_log10
            hits += int(lo <= held <= hi)
            total += 1
    cov = hits / total if total else 0.0
    return Calibration(coverage_90=round(cov, 3), pairs=len([g for g in groups if len(g) >= 3]))


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
