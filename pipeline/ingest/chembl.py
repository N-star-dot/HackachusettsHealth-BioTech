"""ChEMBL ingest: IC50 measurements with their assay + source document.

Free REST API. Release 36 (Oct 2025): ~2.8M compounds, 17,803 targets. Cached on
first pull. Feeds the stage-2 prior and the stage-4 calibration test.

Data-quality rules (critical — a sloppy pull makes the calibration number meaningless):
  * Keep only records with a non-null `pchembl_value`. ChEMBL computes pChEMBL only when
    the relation is '=', units are nM, value > 0, and there is no data-validity flag — so
    this one filter rejects censored values ('>10000' = "no effect at the top dose", NOT
    10000) and quality-flagged records in a single check.
  * Drop `potential_duplicate` records (a later paper re-reporting an earlier measurement),
    which would make labs look like they agree more than they really do.
  * pChEMBL = -log10(IC50 in molar), so 1 nM -> 9. We use pChEMBL as the log-scale value and
    keep standard_value (nM) only for display.
"""

from __future__ import annotations

import math
import statistics
from collections import defaultdict

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


def pchembl_to_nM(pchembl: float) -> float:
    """pChEMBL (-log10 molar) -> nM. 9 -> 1 nM."""
    return 10 ** (9.0 - pchembl)


def _clean_activities(acts: list[dict]) -> list[dict]:
    """Keep only quality IC50 records for the calibration/prior use case:

      * non-null pchembl_value  (rejects censored '>'/'<' and quality-flagged records),
      * not a potential_duplicate,
      * assay_type 'B'          (binding / biochemical on purified protein — exactly what
                                 the app simulates; cell-based 'F' assays give different
                                 numbers and would inflate apparent lab disagreement),
      * wild-type target        (empty assay_variant_mutation).

    Returns normalised rows carrying the log-scale pChEMBL value, the nM value for
    display, and the source document for paper-level collapsing.
    """
    out = []
    for a in acts:
        pch = a.get("pchembl_value")
        if pch is None:
            continue
        if a.get("potential_duplicate"):
            continue
        if a.get("assay_type") != "B":  # binding/biochemical only
            continue
        if a.get("assay_variant_mutation"):  # non-empty -> mutant target, skip
            continue
        try:
            pch = float(pch)
        except (TypeError, ValueError):
            continue
        nM = None
        if a.get("standard_value") is not None:
            try:
                nM = float(a["standard_value"])
            except (TypeError, ValueError):
                nM = None
        out.append({
            "activity_id": a.get("activity_id"),
            "pchembl_value": pch,
            "standard_value_nM": nM if (nM and nM > 0) else pchembl_to_nM(pch),
            "assay_chembl_id": a.get("assay_chembl_id"),
            "document_chembl_id": a.get("document_chembl_id"),
            "molecule_chembl_id": a.get("molecule_chembl_id"),
        })
    return out


def _fetch_clean_activities(
    target_chembl_id: str, max_pages: int = 3, page_size: int = 1000
) -> list[dict]:
    """Paginate the activity endpoint (server-side pchembl + assay_type=B) -> cleaned rows."""
    rows: list[dict] = []
    offset = 0
    for _ in range(max_pages):
        params = {
            "target_chembl_id": target_chembl_id,
            "standard_type": "IC50",
            "standard_units": "nM",
            "pchembl_value__isnull": "false",  # drop censored/flagged early
            "assay_type": "B",                  # binding/biochemical only
            "limit": page_size,
            "offset": offset,
            "format": "json",
        }
        body = cached_get_json("chembl", f"{_BASE}/activity", params=params)
        acts = body.get("activities", [])
        if not acts:
            break
        rows.extend(_clean_activities(acts))
        offset += page_size
        if not body.get("page_meta", {}).get("next"):
            break
    return rows


def _collapse_by_document(rows: list[dict]) -> list[dict]:
    """Collapse records to ONE value per source document: the median pChEMBL of that paper.

    This makes each paper vote once, so a single paper reporting 16 measurements does not
    dominate a group. Returns [{document_chembl_id, pchembl_value, standard_value_nM,
    activity_ids}] sorted for determinism.
    """
    by_doc: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        if r["document_chembl_id"]:
            by_doc[r["document_chembl_id"]].append(r)
    collapsed = []
    for doc, recs in by_doc.items():
        pch_med = statistics.median(r["pchembl_value"] for r in recs)
        collapsed.append({
            "document_chembl_id": doc,
            "pchembl_value": pch_med,
            "standard_value_nM": pchembl_to_nM(pch_med),
            "activity_ids": [r["activity_id"] for r in recs],
        })
    return sorted(collapsed, key=lambda d: d["document_chembl_id"])


def ic50_activities(target_chembl_id: str, limit: int = 100) -> list[dict]:
    """Quality IC50 activity records (nM + pChEMBL) for a target."""
    return _fetch_clean_activities(target_chembl_id, max_pages=1, page_size=limit)


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
