"""ChEMBL ingest: IC50 measurements with their assay + source document.

Free REST API. Release 36 (Oct 2025): ~2.8M compounds, 17,803 targets. Cached on
first pull. Feeds the stage-2 prior and the stage-4 calibration test.

Parsing is split from fetching: `_parse_activities` turns a raw ChEMBL activity body
into clean IC50 records in nM, dropping non-numeric or non-positive values, so a messy
response never poisons the prior or the calibration groups.
"""

from __future__ import annotations

import math
import statistics
from typing import Any

from pipeline.ingest.http_cache import cached_get_json

_BASE = "https://www.ebi.ac.uk/chembl/api/data"

# A diverse set of well-studied human targets across protein families, so the
# calibration set isn't biased to one target type. Names verified against ChEMBL:
#   CHEMBL203  EGFR (kinase)             CHEMBL279  VEGFR2 (kinase)
#   CHEMBL240  hERG / KCNH2 (ion channel)CHEMBL1824 HER2 / erbB-2 (kinase)
#   CHEMBL260  MAPK14 / p38 alpha (kinase)   CHEMBL2971 JAK2 (kinase)
#   CHEMBL233  mu-opioid receptor (GPCR) CHEMBL217  dopamine D2 (GPCR)
#   CHEMBL4005 PI3K alpha (kinase)       CHEMBL2095 FKBP1A / FKBP12 (isomerase)
CALIBRATION_TARGETS: tuple[str, ...] = (
    "CHEMBL203", "CHEMBL279", "CHEMBL240", "CHEMBL1824", "CHEMBL260",
    "CHEMBL2971", "CHEMBL233", "CHEMBL217", "CHEMBL4005", "CHEMBL2095",
)

def _parse_activities(body: Any) -> list[dict]:
    """Normalise a /activity response into clean IC50 records (nM, positive values)."""
    if not isinstance(body, dict):
        return []
    out: list[dict] = []
    for a in body.get("activities", []) or []:
        if not isinstance(a, dict):
            continue
        val = a.get("standard_value")
        if val is None:
            continue
        try:
            value_nM = float(val)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(value_nM) or value_nM <= 0:
            continue
        out.append({
            "activity_id": a.get("activity_id"),
            "standard_value_nM": value_nM,
            "assay_chembl_id": a.get("assay_chembl_id"),
            "document_chembl_id": a.get("document_chembl_id"),
            "molecule_chembl_id": a.get("molecule_chembl_id"),
        })
    return out


def ic50_activities(target_chembl_id: str, limit: int = 100) -> list[dict]:
    """Return IC50 activity records (nM) for a target, each with its activity id.
    [{activity_id, standard_value_nM, assay_chembl_id, document_chembl_id, molecule_chembl_id}]."""
    params = {
        "target_chembl_id": target_chembl_id,
        "standard_type": "IC50",
        "standard_units": "nM",
        "limit": limit,
        "format": "json",
    }
    body = cached_get_json("chembl", f"{_BASE}/activity", params=params)
    return _parse_activities(body)


def prior_ic50_nM(target_chembl_id: str) -> dict | None:
    """Summarise IC50 measurements into a prior: median, n, spread (log10)."""
    acts = ic50_activities(target_chembl_id)
    values = [a["standard_value_nM"] for a in acts if a["standard_value_nM"] > 0]
    if not values:
        return None
    return {
        "document_chembl_id": document_chembl_id,
        "pubmed_id": str(pubmed_id),
        "title": body.get("title"),
        "year": body.get("year"),
        "journal": body.get("journal"),
    }


def prior_ic50_nM(target_chembl_id: str, molecule_chembl_id: str) -> dict | None:
    """Starting-guess prior for one SPECIFIC (target, compound) pair, paper-collapsed.

    Each source paper contributes one value (its median pChEMBL), so a single prolific
    paper can't dominate. Reports the median across papers, the sample SD across papers
    (ddof=1), and the paper count. With fewer than 2 papers we can't estimate a spread, so
    we fall back to 0.68 (Kalliokoski 2013) and flag it.
    """
    rows = [
        a for a in _fetch_clean_activities(target_chembl_id, max_pages=3)
        if a["molecule_chembl_id"] == molecule_chembl_id
    ]
    papers = _collapse_by_document(rows)
    if not papers:
        return None

    values_nM = [p["standard_value_nM"] for p in papers]
    logs = [math.log10(v) for v in values_nM if v > 0]
    if len(logs) >= 2:
        spread = round(statistics.stdev(logs), 3)  # sample SD across papers (ddof=1)
        spread_source = "measured across papers (ddof=1)"
    else:
        spread = 0.68
        spread_source = "default (Kalliokoski 2013; only one paper)"

    activity_ids = [aid for p in papers for aid in p["activity_ids"]]
    return {
        "target_chembl_id": target_chembl_id,
        "molecule_chembl_id": molecule_chembl_id,
        "median_nM": float(statistics.median(values_nM)),
        "n_papers": len(papers),
        "spread_log10": spread,
        "spread_source": spread_source,
        "activity_ids": activity_ids,
        "document_chembl_ids": [p["document_chembl_id"] for p in papers],
        # per-paper detail so a no-network designer can cite each paper's own value
        "papers": [
            {
                "document_chembl_id": p["document_chembl_id"],
                "activity_id": p["activity_ids"][0],
                "value_nM": round(p["standard_value_nM"], 2),
                "pchembl_value": round(p["pchembl_value"], 3),
            }
            for p in papers
        ],
    }


def ic50_pairs_for_target(
    target_chembl_id: str,
    max_pages: int = 3,
    page_size: int = 1000,
    min_papers: int = 3,
) -> list[dict]:
    """Pull quality IC50 activities for a target and build paper-collapsed calibration groups.

    Each (target, compound) group holds ONE value per source paper (the paper's median
    pChEMBL), and must span >= `min_papers` distinct papers — because the calibration test
    asks where a *new paper's* value would land, and multiple values from one paper only
    measure that paper's internal repeatability.

    Returns one record per qualifying pair:
        {target_chembl_id, molecule_chembl_id, values_nM, pchembl_values,
         activity_ids, document_chembl_ids}
    where values_nM/pchembl_values have one entry per paper.
    """
    rows = _fetch_clean_activities(target_chembl_id, max_pages=max_pages, page_size=page_size)

    by_compound: dict[str, list[dict]] = defaultdict(list)
    for a in rows:
        if a["molecule_chembl_id"]:
            by_compound[a["molecule_chembl_id"]].append(a)

    pairs = []
    for mol, recs in by_compound.items():
        papers = _collapse_by_document(recs)  # one value per paper
        if len(papers) >= min_papers:
            pairs.append({
                "target_chembl_id": target_chembl_id,
                "molecule_chembl_id": mol,
                "values_nM": [p["standard_value_nM"] for p in papers],
                "pchembl_values": [p["pchembl_value"] for p in papers],
                "activity_ids": [aid for p in papers for aid in p["activity_ids"]],
                "document_chembl_ids": [p["document_chembl_id"] for p in papers],
            })
    return pairs
