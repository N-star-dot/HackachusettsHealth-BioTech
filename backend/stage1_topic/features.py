"""Momentum-model feature engineering. Owner A.

Strict train/label separation to prevent leakage:
  * FEATURES are computed from publication counts 2015-2019 ONLY.
  * The LABEL is computed from 2020-2024 growth and is NOT a feature.
  * 2025-2026 are ignored everywhere (OpenAlex indexing lags for recent years).

The label answers the spec's question: did this topic grow faster than the median
topic from 2020-2024? Per-topic growth is the slope of log10(counts) over 2020-2024;
the median is computed across the whole topic set (see scripts/build_training_data.py).

Feature design (v3). v1 used three noise features; v2 replaced them with recency /
log-ratio / field-relative slopes that turned out to be 0.97-0.99 correlated with the
plain slope, so they added no information and the model only tied the baseline.

v3 keeps the two features that carry independent signal and adds three SHAPE features
of the 2015-2019 log10(count+1) curve that are only weakly correlated with the slope
(~0.14, 0.47, 0.02), so they genuinely add information:

  * log_slope        — OLS slope of log10 counts 2015-2019 (the baseline signal).
  * mean_log_level   — mean log10 count: how crowded the topic already is
                       (the product thesis rewards SMALL but accelerating topics).
  * volatility       — std of residuals around the OLS line (ddof=2): how noisy the trend.
  * last_year_jump   — log(2019) - log(2018): the most recent year-on-year move.
  * curvature        — quadratic coefficient of a degree-2 fit (x centred on 2017):
                       is the trend bending up (+) or down (-)?

All five use only 2015-2019 counts, so nothing from the label window can leak in.
"""

from __future__ import annotations

import math
import statistics

FEATURE_YEARS = (2015, 2016, 2017, 2018, 2019)
LABEL_YEARS = (2020, 2021, 2022, 2023, 2024)
_CENTRE_YEAR = 2017  # centre x for the curvature polynomial fit

# Order matters: it's the column order the model trains/predicts on.
FEATURE_NAMES = (
    "log_slope",
    "mean_log_level",
    "volatility",
    "last_year_jump",
    "curvature",
)


def _counts_map(counts_by_year: list[dict]) -> dict[int, int]:
    return {int(c["year"]): int(c["works"]) for c in counts_by_year}


def _ols_slope(years: list[int], values: list[float]) -> float:
    """Ordinary least-squares slope of y vs x."""
    n = len(years)
    if n < 2:
        return 0.0
    mx = sum(years) / n
    my = sum(values) / n
    denom = sum((x - mx) ** 2 for x in years)
    if denom == 0:
        return 0.0
    return sum((x - mx) * (y - my) for x, y in zip(years, values)) / denom


def _residual_std(years: list[int], values: list[float]) -> float:
    """Std of residuals around the OLS line, dividing by n-2 (regression ddof)."""
    n = len(years)
    if n <= 2:
        return 0.0
    slope = _ols_slope(years, values)
    mx = sum(years) / n
    my = sum(values) / n
    intercept = my - slope * mx
    resid = [y - (slope * x + intercept) for x, y in zip(years, values)]
    sse = sum(r * r for r in resid)
    return math.sqrt(sse / (n - 2))


def _curvature(years: list[int], values: list[float]) -> float:
    """Quadratic coefficient of a degree-2 polynomial fit, x centred on _CENTRE_YEAR.

    Pure-Python normal-equation solve for a 3x3 system (no numpy dependency here so the
    feature code stays importable anywhere). Returns the coefficient of x^2.
    """
    xs = [y - _CENTRE_YEAR for y in years]
    ys = values
    n = len(xs)
    if n < 3:
        return 0.0
    # moments
    s0 = n
    s1 = sum(xs)
    s2 = sum(x**2 for x in xs)
    s3 = sum(x**3 for x in xs)
    s4 = sum(x**4 for x in xs)
    t0 = sum(ys)
    t1 = sum(x * y for x, y in zip(xs, ys))
    t2 = sum((x**2) * y for x, y in zip(xs, ys))
    # Solve [[s0,s1,s2],[s1,s2,s3],[s2,s3,s4]] [c0,c1,c2]^T = [t0,t1,t2]^T
    A = [[s0, s1, s2], [s1, s2, s3], [s2, s3, s4]]
    b = [t0, t1, t2]
    sol = _solve3(A, b)
    return sol[2] if sol is not None else 0.0


def _solve3(A: list[list[float]], b: list[float]) -> list[float] | None:
    """Gaussian elimination for a 3x3 system. Returns None if singular."""
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for col in range(3):
        # partial pivot
        piv = max(range(col, 3), key=lambda r: abs(M[r][col]))
        if abs(M[piv][col]) < 1e-12:
            return None
        M[col], M[piv] = M[piv], M[col]
        pv = M[col][col]
        M[col] = [v / pv for v in M[col]]
        for r in range(3):
            if r != col:
                factor = M[r][col]
                M[r] = [v - factor * mc for v, mc in zip(M[r], M[col])]
    return [M[0][3], M[1][3], M[2][3]]


def compute_features(counts_by_year: list[dict]) -> dict | None:
    """Per-topic features from 2015-2019 counts only. None if the window is too sparse."""
    m = _counts_map(counts_by_year)
    series = [m.get(y, 0) for y in FEATURE_YEARS]
    if sum(1 for v in series if v > 0) < 3:
        return None

    years = list(FEATURE_YEARS)
    log_series = [math.log10(v + 1.0) for v in series]

    log_slope = _ols_slope(years, log_series)
    mean_log_level = statistics.mean(log_series)
    volatility = _residual_std(years, log_series)
    # last_year_jump: log(2019) - log(2018)
    idx_2018 = FEATURE_YEARS.index(2018)
    idx_2019 = FEATURE_YEARS.index(2019)
    last_year_jump = log_series[idx_2019] - log_series[idx_2018]
    curvature = _curvature(years, log_series)

    return {
        "log_slope": round(log_slope, 6),
        "mean_log_level": round(mean_log_level, 6),
        "volatility": round(volatility, 6),
        "last_year_jump": round(last_year_jump, 6),
        "curvature": round(curvature, 6),
    }


def label_growth(counts_by_year: list[dict]) -> float | None:
    """Per-topic 2020-2024 growth = slope of log10(counts). None if too sparse."""
    m = _counts_map(counts_by_year)
    series = [m.get(y, 0) for y in LABEL_YEARS]
    if sum(1 for v in series if v > 0) < 3:
        return None
    log_series = [math.log10(v + 1.0) for v in series]
    return _ols_slope(list(LABEL_YEARS), log_series)


def feature_vector(features: dict) -> list[float]:
    """Flatten a features dict into the fixed FEATURE_NAMES order for the model."""
    return [float(features[name]) for name in FEATURE_NAMES]


def slope_baseline_score(features: dict) -> float:
    """The baseline the model must beat: 2015-2019 OLS slope alone."""
    return float(features["log_slope"])
