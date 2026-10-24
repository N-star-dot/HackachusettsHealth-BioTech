"""Train the momentum model from the topic_features table.

    python scripts/train_momentum.py

Reads labelled rows written by build_training_data.py, evaluates with
RepeatedStratifiedKFold (5x5), reports AUROC vs the slope-only baseline and the
top-decile precision, fits the final model on all rows, and pickles it to
models/momentum_hgb.pkl.
"""

from __future__ import annotations

import sys

from backend.stage1_topic.momentum_model import train
from database import get_db


def main() -> int:
    db = get_db()
    rows = db.all_topic_features()
    labelled = [r for r in rows if r.get("label") is not None]
    print(f"Loaded {len(labelled)} labelled topics from topic_features.")
    if len(labelled) < 50:
        print("Not enough data. Run: python scripts/build_training_data.py", file=sys.stderr)
        return 1

    m = train(labelled)
    print("\n=== Momentum model trained ===")
    for k, v in m.items():
        print(f"  {k}: {v}")

    print(
        f"\nSlide line: AUROC {m['model_auroc_mean']} ± {m['model_auroc_std']} "
        f"vs {m['baseline_auroc_mean']} ± {m['baseline_auroc_std']} baseline, "
        f"wins {m['folds_model_wins']} of {m['folds_total']}."
    )
    print(
        f"Top-10% picks in real top-25% growers: "
        f"{m['top10pct_in_top25pct_model']} (model) vs "
        f"{m['top10pct_in_top25pct_baseline']} (slope); chance = 0.25."
    )
    if m["beats_baseline"]:
        print("\n✓ Model beats the slope-only baseline on repeated CV — it earns its place.")
    else:
        print("\n✗ Model does not clearly beat the baseline. Report the CV numbers honestly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
