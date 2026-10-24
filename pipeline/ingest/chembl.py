"""ChEMBL ingest: IC50 measurements with their assay + source document.

Free REST API. Release 36 (Oct 2025): ~2.8M compounds, 17,803 targets. Cached on
first pull. Feeds the stage-2 prior and the stage-4 calibration test.
"""

from __future__ import annotations

from collections import defaultdict

from pipeline.ingest.http_cache import cached_get_json

_BASE = "https://www.ebi.ac.uk/chembl/api/data"

# A diverse set of well-studied human targets across protein families, so the
# calibration set isn't biased to one target type. ChEMBL target ids:
#   CHEMBL203  EGFR (kinase)        CHEMBL279  VEGFR2 (kinase)
#   CHEMBL240  hERG (ion channel)   CHEMBL1824 HER2 (kinase)
#   CHEMBL260  CDK2 (kinase)        CHEMBL2971 JAK2 (kinase)
#   CHEMBL233  mu opioid (GPCR)     CHEMBL217  dopamine D2 (GPCR)
#   CHEMBL4005 PI3K alpha           CHEMBL2095  COX (enzyme)
CALIBRATION_TARGETS: tuple[str, ...] = (
    "CHEMBL203", "CHEMBL279", "CHEMBL240", "CHEMBL1824", "CHEMBL260",
    "CHEMBL2971", "CHEMBL233", "CHEMBL217", "CHEMBL4005", "CHEMBL2095",
)


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


def ic50_pairs_for_target(
    target_chembl_id: str, max_pages: int = 3, page_size: int = 1000, min_values: int = 3
) -> list[dict]:
    """Pull IC50 activities for a target and group them by compound.

    Returns one record per (target, compound) pair that has >= `min_values` IC50
    measurements:
        {target_chembl_id, molecule_chembl_id, values_nM: [...], activity_ids: [...]}
    These are the repeated-measurement groups the calibration test holds one value out
    of. Each page response is cached, so re-runs are offline and free.
    """
    by_compound: dict[str, dict] = defaultdict(lambda: {"values_nM": [], "activity_ids": []})
    offset = 0
    for _ in range(max_pages):
        params = {
            "target_chembl_id": target_chembl_id,
            "standard_type": "IC50",
            "standard_units": "nM",
            "limit": page_size,
            "offset": offset,
            "format": "json",
        }
        body = cached_get_json("chembl", f"{_BASE}/activity", params=params)
        acts = body.get("activities", [])
        if not acts:
            break
        for a in acts:
            val = a.get("standard_value")
            mol = a.get("molecule_chembl_id")
            if val is None or mol is None:
                continue
            try:
                v = float(val)
            except (TypeError, ValueError):
                continue
            if v <= 0:
                continue
            by_compound[mol]["values_nM"].append(v)
            by_compound[mol]["activity_ids"].append(a.get("activity_id"))
        offset += page_size
        # stop early if the API says there are no more pages
        if not body.get("page_meta", {}).get("next"):
            break

    pairs = []
    for mol, rec in by_compound.items():
        if len(rec["values_nM"]) >= min_values:
            pairs.append({
                "target_chembl_id": target_chembl_id,
                "molecule_chembl_id": mol,
                "values_nM": rec["values_nM"],
                "activity_ids": rec["activity_ids"],
            })
    return pairs
