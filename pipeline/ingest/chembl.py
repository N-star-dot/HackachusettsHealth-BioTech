"""ChEMBL ingest: IC50 measurements with their assay + source document.

Free REST API. Release 36 (Oct 2025): ~2.8M compounds, 17,803 targets. Cached on
first pull. Feeds the stage-2 prior and the stage-4 calibration test.
"""

from __future__ import annotations

from pipeline.ingest.http_cache import cached_get_json

_BASE = "https://www.ebi.ac.uk/chembl/api/data"


def ic50_activities(target_chembl_id: str, limit: int = 100) -> list[dict]:
    """Return IC50 activity records (nM) for a target, each with its activity id.
    [{activity_id, standard_value_nM, assay_chembl_id, document_chembl_id}]."""
    params = {
        "target_chembl_id": target_chembl_id,
        "standard_type": "IC50",
        "standard_units": "nM",
        "limit": limit,
        "format": "json",
    }
    body = cached_get_json("chembl", f"{_BASE}/activity", params=params)
    out = []
    for a in body.get("activities", []):
        val = a.get("standard_value")
        if val is None:
            continue
        try:
            out.append({
                "activity_id": a.get("activity_id"),
                "standard_value_nM": float(val),
                "assay_chembl_id": a.get("assay_chembl_id"),
                "document_chembl_id": a.get("document_chembl_id"),
                "molecule_chembl_id": a.get("molecule_chembl_id"),
            })
        except (TypeError, ValueError):
            continue
    return out


def prior_ic50_nM(target_chembl_id: str) -> dict | None:
    """Summarise IC50 measurements into a prior: median, n, spread (log10)."""
    import math
    import statistics

    acts = ic50_activities(target_chembl_id)
    values = [a["standard_value_nM"] for a in acts if a["standard_value_nM"] > 0]
    if not values:
        return None
    logs = [math.log10(v) for v in values]
    spread = statistics.pstdev(logs) if len(logs) > 1 else 0.68
    return {
        "median_nM": float(statistics.median(values)),
        "n_measurements": len(values),
        "spread_log10": round(spread, 3),
        "activity_ids": [a["activity_id"] for a in acts[:10]],
    }
