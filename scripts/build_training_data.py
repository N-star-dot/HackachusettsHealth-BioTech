"""Populate the `topic_features` table for the momentum model.

Pulls every life/health-science topic from OpenAlex, fetches its 2015-2024 yearly
counts (cached), computes leakage-safe features (2015-2019) and the growth quantity
(2020-2024), then labels each topic 1 if its 2020-2024 growth beats the MEDIAN topic's.

Run once (or with --refresh to re-pull):
    python scripts/build_training_data.py                 # all topics
    python scripts/build_training_data.py --max 500       # cap for a quick pass
    python scripts/build_training_data.py --refresh       # bypass cache

Everything is cached in the api_cache table, so re-runs are free and offline.
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time

# Load .env so OPENALEX_API_KEY / CONTACT_EMAIL are available.
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

from backend.stage1_topic.features import compute_features, label_growth
from database import get_db
from pipeline.ingest import openalex


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=None, help="cap number of topics (debug)")
    ap.add_argument("--refresh", action="store_true", help="bypass cache on count pulls")
    args = ap.parse_args()

    db = get_db()

    print("Enumerating life/health-science topics from OpenAlex...")
    topics = openalex.enumerate_life_science_topics(max_topics=args.max)
    print(f"  found {len(topics)} topics")

    # --- pass 1: pull counts, compute features + raw growth ---
    staged: list[dict] = []
    t0 = time.perf_counter()
    for i, t in enumerate(topics, 1):
        try:
            counts = openalex.works_by_year(t["openalex_id"])
        except Exception as exc:  # network hiccup on one topic shouldn't kill the run
            print(f"  [{i}/{len(topics)}] {t['openalex_id']} FAILED: {exc}")
            continue
        counts_rows = [{"year": c["year"], "works": c["works"]} for c in counts]
        feats = compute_features(counts_rows)
        growth = label_growth(counts_rows)
        if feats is None or growth is None:
            continue  # too sparse to use
        feats["field"] = t.get("field")  # categorical feature kept alongside
        staged.append(
            {"openalex_id": t["openalex_id"], "name": t["name"], "features": feats, "growth": growth}
        )
        if i % 100 == 0:
            rate = i / (time.perf_counter() - t0)
            print(f"  [{i}/{len(topics)}] usable={len(staged)}  ({rate:.1f} topics/s)")

    if not staged:
        print("No usable topics — check network / API key.", file=sys.stderr)
        return 1

    # --- pass 2: label by the MEDIAN growth across all usable topics ---
    median_growth = statistics.median(s["growth"] for s in staged)
    print(f"\nMedian 2020-2024 log-growth across {len(staged)} topics: {median_growth:.5f}")

    pos = 0
    for s in staged:
        label = 1 if s["growth"] > median_growth else 0
        pos += label
        db.upsert_topic_features(
            s["openalex_id"], s["name"], s["features"], label, growth=s["growth"]
        )

    print(f"Wrote {len(staged)} rows to topic_features "
          f"({pos} positive / {len(staged) - pos} negative).")
    print("Done. Train with: python scripts/train_momentum.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
