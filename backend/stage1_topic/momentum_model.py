"""Momentum model: train, persist, and load. Owner A.

A `HistGradientBoostingClassifier` predicting p(topic grows faster than the median
topic, 2020-2024) from leakage-safe 2015-2019 features plus the topic's field.

Evaluation uses RepeatedStratifiedKFold (5 splits x 5 repeats = 25 test sets), because a
single 80/20 split swings by ~±0.025 AUROC — bigger than the model-vs-baseline gap. We
report mean±std AUROC for the model and the slope-only baseline, the mean PAIRED
difference, how many of the 25 folds the model wins, and a top-decile precision metric
(share of the model's top 10% that land in the real top 25% of 2020-2024 growth).

The final model is fit on ALL rows and pickled to models/momentum_hgb.pkl; stage 1 loads
it and falls back to the slope heuristic if absent.
"""

from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np

from backend.stage1_topic.features import FEATURE_NAMES

MODEL_VERSION = "hgb-v3"
MODEL_PATH = Path(__file__).resolve().parents[2] / "models" / "momentum_hgb.pkl"

# Numeric features (FEATURE_NAMES) followed by a one-hot of `field`. The fitted field
# vocabulary is stored so predict-time encoding matches train-time.


def _vectorise(rows: list[dict], field_vocab: list[str]) -> np.ndarray:
    field_index = {f: i for i, f in enumerate(field_vocab)}
    X = []
    for r in rows:
        feats = r["features"]
        num = [float(feats[name]) for name in FEATURE_NAMES]
        onehot = [0.0] * len(field_vocab)
        fi = field_index.get(feats.get("field"))
        if fi is not None:
            onehot[fi] = 1.0
        X.append(num + onehot)
    return np.array(X, dtype=float)


def _make_clf(seed: int):
    from sklearn.ensemble import HistGradientBoostingClassifier

    return HistGradientBoostingClassifier(
        max_iter=200,
        learning_rate=0.05,
        max_depth=3,
        max_leaf_nodes=15,
        min_samples_leaf=30,
        l2_regularization=5.0,
        early_stopping=True,
        validation_fraction=0.15,
        random_state=seed,
    )


def _top_decile_precision(scores: np.ndarray, growth: np.ndarray) -> float:
    """Share of the top-10% scored topics that fall in the actual top-25% of growth.
    Chance level is 0.25. Returns nan if growth is unavailable."""
    if growth is None or np.all(np.isnan(growth)):
        return float("nan")
    n = len(scores)
    k = max(1, n // 10)
    top_idx = np.argsort(scores)[::-1][:k]
    growth_cut = np.nanpercentile(growth, 75)
    in_top25 = growth[top_idx] >= growth_cut
    return float(np.mean(in_top25))


def train(rows: list[dict], seed: int = 0) -> dict:
    """Train + evaluate with RepeatedStratifiedKFold. Returns the full metric bundle.

    Each row may optionally carry 'growth' (the raw 2020-2024 log-slope) so we can report
    top-decile precision; if absent, that metric is reported as nan.
    """
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import RepeatedStratifiedKFold

    rows = [r for r in rows if r.get("label") is not None]
    if len(rows) < 50:
        raise ValueError(f"need >=50 labelled rows, have {len(rows)}")

    field_vocab = sorted({r["features"].get("field") for r in rows if r["features"].get("field")})
    X = _vectorise(rows, field_vocab)
    y = np.array([int(r["label"]) for r in rows])
    slope_idx = FEATURE_NAMES.index("log_slope")
    slope_scores = X[:, slope_idx]
    growth = np.array(
        [float(r["growth"]) if r.get("growth") is not None else np.nan for r in rows]
    )

    rkf = RepeatedStratifiedKFold(n_splits=5, n_repeats=5, random_state=seed)
    model_aucs: list[float] = []
    base_aucs: list[float] = []
    model_prec: list[float] = []
    base_prec: list[float] = []

    for tr, te in rkf.split(X, y):
        clf = _make_clf(seed)
        clf.fit(X[tr], y[tr])
        p_te = clf.predict_proba(X[te])[:, 1]
        model_aucs.append(roc_auc_score(y[te], p_te))
        base_aucs.append(roc_auc_score(y[te], slope_scores[te]))
        model_prec.append(_top_decile_precision(p_te, growth[te]))
        base_prec.append(_top_decile_precision(slope_scores[te], growth[te]))

    m = np.array(model_aucs)
    b = np.array(base_aucs)
    paired = m - b
    wins = int((m > b).sum())

    # --- fit final model on ALL rows and persist ---
    final = _make_clf(seed)
    final.fit(X, y)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MODEL_PATH, "wb") as fh:
        pickle.dump(
            {"clf": final, "field_vocab": field_vocab, "feature_names": FEATURE_NAMES,
             "version": MODEL_VERSION},
            fh,
        )

    return {
        "model": MODEL_VERSION,
        "n_rows": int(len(y)),
        "cv": "RepeatedStratifiedKFold(5x5=25)",
        "model_auroc_mean": round(float(m.mean()), 4),
        "model_auroc_std": round(float(m.std()), 4),
        "baseline_auroc_mean": round(float(b.mean()), 4),
        "baseline_auroc_std": round(float(b.std()), 4),
        "mean_paired_delta": round(float(paired.mean()), 4),
        "folds_model_wins": wins,
        "folds_total": len(m),
        "beats_baseline": bool(paired.mean() > 0 and wins > len(m) / 2),
        "top10pct_in_top25pct_model": round(float(np.nanmean(model_prec)), 4),
        "top10pct_in_top25pct_baseline": round(float(np.nanmean(base_prec)), 4),
        "model_path": str(MODEL_PATH),
    }


_cache: dict | None = None


def load_model() -> dict | None:
    """Load the pickled model bundle, or None if it hasn't been trained yet."""
    global _cache
    if _cache is not None:
        return _cache
    if not MODEL_PATH.exists():
        return None
    with open(MODEL_PATH, "rb") as fh:
        _cache = pickle.load(fh)
    return _cache


def predict_p_growth(features: dict) -> float | None:
    """p(growth) for one topic's feature dict, or None if no model is trained."""
    bundle = load_model()
    if bundle is None:
        return None
    X = _vectorise([{"features": features}], bundle["field_vocab"])
    return float(bundle["clf"].predict_proba(X)[:, 1][0])
