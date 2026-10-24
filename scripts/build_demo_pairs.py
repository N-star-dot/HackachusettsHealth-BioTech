"""Write the 3 demo (target, compound) pairs to data/demo/demo_pairs.json.

These are approved/well-studied drugs on their intended targets, each backed by many
independent papers, so every demo number traces to real ChEMBL measurements. The designer
reads this file instead of the CHEMBL0000 / fixed-120nM placeholders; regenerating it
updates the demo automatically.

    python scripts/build_demo_pairs.py        # after build_calibration_data.py

Chosen pairs:
  * lapatinib   on HER2   (CHEMBL554   / CHEMBL1824)
  * SB-203580   on p38α   (CHEMBL10    / CHEMBL260)   [MAPK14]
  * tofacitinib on JAK2   (CHEMBL221959/ CHEMBL2971)  [approved drug on intended target;
                           replaces erlotinib-on-HER2, which only hits HER2 weakly]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

from pipeline.ingest import chembl

_OUT = Path(__file__).resolve().parents[1] / "data" / "demo" / "demo_pairs.json"

# (label, compound_chembl_id, target_chembl_id)
DEMO_PAIRS = [
    ("lapatinib on HER2", "CHEMBL554", "CHEMBL1824"),
    ("SB-203580 on p38alpha (MAPK14)", "CHEMBL10", "CHEMBL260"),
    ("tofacitinib on JAK2", "CHEMBL221959", "CHEMBL2971"),
]


def main() -> int:
    demo_pairs = []
    for label, compound, target in DEMO_PAIRS:
        prior = chembl.prior_ic50_nM(target, compound)
        if prior is None:
            print(f"  WARNING: no quality data for {label} ({compound}/{target})", file=sys.stderr)
            continue
        demo_pairs.append({
            "label": label,
            "target_chembl_id": target,
            "compound_chembl_id": compound,
            "prior": prior,
            "activity_ids": prior["activity_ids"],
            "document_ids": prior["document_chembl_ids"],
        })

    if not demo_pairs:
        print("No demo pairs resolved — run build_calibration_data.py and check network.",
              file=sys.stderr)
        return 1

    _OUT.parent.mkdir(parents=True, exist_ok=True)
    _OUT.write_text(json.dumps(demo_pairs, indent=2))
    print(f"Wrote {len(demo_pairs)} demo pairs to {_OUT}")
    for p in demo_pairs:
        pr = p["prior"]
        print(f"  {p['label']}: median={pr['median_nM']:.1f} nM, "
              f"spread={pr['spread_log10']} ({pr['n_papers']} papers)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
