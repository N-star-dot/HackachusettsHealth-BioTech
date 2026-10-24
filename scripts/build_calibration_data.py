"""Populate the `calibration_groups` table with real ChEMBL IC50 measurement groups.

Pulls binding/biochemical (assay_type B) IC50 activities on wild-type targets, collapses
each source paper to one value (its median pChEMBL), and keeps every (target, compound)
pair backed by >=3 distinct papers. The uncertainty engine's calibration test holds one
PAPER out of each group and checks whether its 90% interval covers it — this proves the
noise model is honest against real cross-lab variability, not single-lab repeatability.

    python scripts/build_calibration_data.py
    python scripts/build_calibration_data.py --targets CHEMBL203 CHEMBL279
    python scripts/build_calibration_data.py --pages 5

Every ChEMBL page is cached in api_cache, so re-runs are offline and free.
"""

from __future__ import annotations

import argparse
import math
import sys

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

from backend.stage4_uncertainty.calibration import pooled_within_group_sd
from database import get_db
from pipeline.ingest import chembl


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", nargs="*", default=list(chembl.CALIBRATION_TARGETS),
                    help="ChEMBL target ids to pull (default: the curated diverse set)")
    ap.add_argument("--pages", type=int, default=3, help="activity pages per target (1000/page)")
    ap.add_argument("--min-papers", type=int, default=3, help="min distinct papers per pair")
    args = ap.parse_args()

    db = get_db()
    # clear any stale groups from an earlier (pre-filter) pull so we don't mix junk in
    db._conn.execute("DELETE FROM calibration_groups")
    db._conn.commit()

    total_pairs = 0
    all_group_values: list[list[float]] = []

    for tid in args.targets:
        try:
            pairs = chembl.ic50_pairs_for_target(
                tid, max_pages=args.pages, min_papers=args.min_papers
            )
        except Exception as exc:
            print(f"  target {tid} FAILED: {exc}", file=sys.stderr)
            continue
        for p in pairs:
            db.upsert_calibration_group(
                p["target_chembl_id"], p["molecule_chembl_id"],
                p["values_nM"], p["activity_ids"], document_ids=p["document_chembl_ids"],
            )
            all_group_values.append(p["values_nM"])
        total_pairs += len(pairs)
        print(f"  {tid}: {len(pairs)} pairs with >={args.min_papers} independent papers")

    if total_pairs == 0:
        print("No calibration pairs pulled — check network.", file=sys.stderr)
        return 1

    pooled = pooled_within_group_sd(all_group_values)
    print(f"\nWrote {total_pairs} calibration groups to calibration_groups.")
    print(f"Pooled within-group SD: {pooled:.3f} log10 units "
          f"(Kalliokoski 2013 reports ~0.68 across ChEMBL).")
    print("Validate with: python scripts/eval_metrics.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
