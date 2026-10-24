"""End-to-end CLI demo: run the whole pipeline for a topic and print each contract.

    python scripts/demo.py "kinase inhibitors for liver fibrosis"

Runs entirely offline (stages use mocks/stubs; stage 4 is a real Monte Carlo).
"""

from __future__ import annotations

import json
import sys

from pipeline import run_pipeline


def main() -> int:
    query = sys.argv[1] if len(sys.argv) > 1 else "kinase inhibitors for liver fibrosis"
    print(f"\n=== Running pipeline for: {query!r} ===\n")
    result = run_pipeline(query, persist=True)

    print(f"run_id: {result.run_id}")
    print(f"blocked by safety gate: {result.blocked}\n")

    print("--- Stage 1: TopicReport ---")
    print(json.dumps(result.topic.model_dump(by_alias=True), indent=2)[:800], "...\n")

    if result.blocked:
        print("Safety gate failed; pipeline stopped. Reasons:", result.topic.safety.reasons)
        return 0

    print("--- Stage 3: SimResult (Opentrons) ---")
    print(f"  pass={result.sim.simulator.passed}  seconds={result.sim.simulator.seconds}  "
          f"error={result.sim.simulator.error}")
    print(f"  cost: {result.sim.cost.model_dump()}\n")

    print("--- Stage 4: UncertaintyReport (1000-run Monte Carlo) ---")
    u = result.uncertainty
    print(f"  fold_error median={u.fold_error.median:.3f}  p90={u.fold_error.p90:.3f}")
    print(f"  outside_range_share={u.outside_range_share:.3f}  failed_fit_share={u.failed_fit_share:.3f}")
    print("  next experiments (ranked by info gained per cost):")
    for ne in u.next_experiments:
        print(f"    - {ne.change}: p90 drop {ne.p90_fold_error_drop_pct}%  score {ne.score}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
