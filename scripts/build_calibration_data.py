"""Populate the `calibration_groups` table with real ChEMBL IC50 measurement groups.

Pulls IC50 activities for a diverse set of well-studied targets, groups them by
(target, compound), and stores every pair with >=3 measurements. The uncertainty
engine's calibration test holds one value out of each group and checks whether its
90% interval covers it — this is how we prove the noise model is honest against REAL
lab-to-lab variability, not a synthetic assumption.

    python scripts/build_calibration_data.py
    python scripts/build_calibration_data.py --targets CHEMBL203 CHEMBL279
    python scripts/build_calibration_data.py --pages 5

Every ChEMBL page is cached in api_cache, so re-runs are offline and free.
"""

from __future__ import annotations

import argparse
import statistics
import sys

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

import math

from database import get_db
from pipeline.ingest import chembl


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", nargs="*", default=list(chembl.CALIBRATION_TARGETS),
                    help="ChEMBL target ids to pull (default: the curated diverse set)")
    ap.add_argument("--pages", type=int, default=3, help="activity pages per target (1000/page)")
    ap.add_argument("--min-values", type=int, default=3, help="min IC50 measurements per pair")
    args = ap.parse_args()

    db = get_db()
    total_pairs = 0
    all_spreads: list[float] = []

    for tid in args.targets:
        try:
            pairs = chembl.ic50_pairs_for_target(
                tid, max_pages=args.pages, min_values=args.min_values
            )
        except Exception as exc:
            print(f"  target {tid} FAILED: {exc}", file=sys.stderr)
            continue
        for p in pairs:
            db.upsert_calibration_group(
                p["target_chembl_id"], p["molecule_chembl_id"],
                p["values_nM"], p["activity_ids"],
            )
            logs = [math.log10(v) for v in p["values_nM"] if v > 0]
            if len(logs) > 1:
                all_spreads.append(statistics.pstdev(logs))
        total_pairs += len(pairs)
        print(f"  {tid}: {len(pairs)} pairs with >={args.min_values} IC50 values")

    if total_pairs == 0:
        print("No calibration pairs pulled — check network.", file=sys.stderr)
        return 1

    median_spread = statistics.median(all_spreads) if all_spreads else float("nan")
    print(f"\nWrote {total_pairs} calibration groups to calibration_groups.")
    print(f"Median within-pair IC50 spread: {median_spread:.3f} log10 units "
          f"(Kalliokoski 2013 reports ~0.68 across ChEMBL).")
    print("Validate with: python scripts/eval_metrics.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
