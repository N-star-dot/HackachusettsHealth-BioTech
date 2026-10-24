"""Write models/metrics.json for GET /api/metrics (B2.3).

Collects the reported numbers — momentum AUROC vs baseline, top-decile precision,
calibration coverage, simulator pass rate, citation error rate — each with a one-line
description, so the dashboard's model card reads them without recomputing per request.

    python scripts/build_metrics.py
"""

from __future__ import annotations

import json
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

_OUT = Path(__file__).resolve().parents[1] / "models" / "metrics.json"


def main() -> int:
    from backend.stage1_topic.momentum_model import train
    from backend.stage2_design import check_citations, citation_error_rate, design_experiment, get_demo_pair
    from backend.stage2_design.demo_pairs import evidence_abstracts_for
    from backend.stage3_protocol import compile_design, simulate_protocol
    from backend.stage4_uncertainty import coverage_90, pooled_within_group_sd
    from database import get_db

    db = get_db()
    metrics: dict = {}

    # momentum
    rows = [r for r in db.all_topic_features() if r.get("label") is not None]
    if len(rows) >= 50:
        m = train(rows)
        metrics["momentum"] = {
            "auroc": m["model_auroc_mean"], "auroc_std": m["model_auroc_std"],
            "baseline_auroc": m["baseline_auroc_mean"], "folds_won": m["folds_model_wins"],
            "folds_total": m["folds_total"],
            "top10pct_in_top25pct": m["top10pct_in_top25pct_model"],
            "description": "RepeatedStratifiedKFold AUROC vs the slope-only baseline "
                           "(model must beat it to earn its place).",
        }

    # calibration
    groups = [r["values_nM"] for r in db.all_calibration_groups() if len(r["values_nM"]) >= 3]
    if groups:
        cal = coverage_90(groups, spread_log10=0.68)
        metrics["calibration"] = {
            "coverage_at_0.68": cal.coverage_90, "pairs": cal.pairs,
            "pooled_within_group_sd": round(pooled_within_group_sd(groups), 3),
            "description": "Share of held-out real ChEMBL papers inside the 90% range at "
                           "the published 0.68 spread (no widening).",
        }

    # simulator pass rate + citation error rate on the 3 demo pairs
    passes = 0
    cite_before = []
    pairs = db.get_report  # noqa: F841 (keep import side effects minimal)
    from backend.stage2_design import load_demo_pairs

    demo = load_demo_pairs()
    for p in demo:
        cid = p["compound_chembl_id"]
        d = design_experiment(compound_chembl_id=cid)
        sim = simulate_protocol(compile_design(d), d)
        passes += 1 if sim.simulator.passed else 0
        d = check_citations(d, pair=get_demo_pair(cid), evidence_abstracts=evidence_abstracts_for(cid))
        cite_before.append(citation_error_rate(d))
    if demo:
        metrics["simulator_pass_rate"] = {
            "value": round(passes / len(demo), 3),
            "description": "Share of compiled demo designs that pass the Opentrons simulator.",
        }
        metrics["citation_error_rate"] = {
            "value": round(sum(cite_before) / len(cite_before), 3),
            "description": "Share of rationale items not fully verified by the checker.",
        }

    _OUT.parent.mkdir(parents=True, exist_ok=True)
    _OUT.write_text(json.dumps(metrics, indent=2))
    print(f"Wrote {_OUT}")
    print(json.dumps(metrics, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
