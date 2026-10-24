"""Stage 2: experiment design. Owner B.

The deterministic designer builds a valid ExperimentDesign from a real demo pair with
NO network and NO LLM, so the pipeline always runs offline. Every design number is
derived from the ChEMBL prior alone; every rationale claim cites one source paper's own
ChEMBL activity record, so the checker can verify it mechanically.

The LLM designer (step 5, designer_llm.py) only writes rationale items on top of this.
"""

from __future__ import annotations

import math

from backend.contracts import (
    Assay,
    Controls,
    Dilution,
    ExperimentDesign,
    Plate,
    PriorIC50,
    RationaleItem,
    Source,
    Volumes,
)
from backend.contracts.common import (
    SourceType,
    chembl_compound_url,
    chembl_document_url,
    source_url,
)
from backend.stage2_design.demo_pairs import get_demo_pair

_MAX_TOP_nM = 100_000.0
_WELLS = 96


def _derive_dilution(median_nM: float, spread_log10: float) -> tuple[Dilution, bool]:
    """Derive the dilution from the prior only (spec step 1). Returns (dilution, capped)."""
    h = max(2.0, 1.645 * spread_log10)
    uncapped_top = median_nM * (10 ** h)
    top_nM = min(uncapped_top, _MAX_TOP_nM)
    capped = uncapped_top > _MAX_TOP_nM
    factor = 3.0
    points = math.ceil(2 * h / math.log10(3.0)) + 1
    return Dilution(top_nM=top_nM, factor=factor, points=points), capped


def design_from_pair(pair: dict, design_id: str = "d-001") -> ExperimentDesign:
    """Build a deterministic ExperimentDesign from a demo pair dict."""
    prior = pair["prior"]
    median_nM = float(prior["median_nM"])
    spread = float(prior["spread_log10"])
    target = pair["target_chembl_id"]
    compound = pair["compound_chembl_id"]

    dilution, capped = _derive_dilution(median_nM, spread)
    replicates = 3
    controls = Controls(positive_wells=4, negative_wells=4)

    # well-budget guard (spec): points*replicates + controls <= 96
    used = dilution.points * replicates + controls.positive_wells + controls.negative_wells
    assert used <= _WELLS, f"design needs {used} wells > {_WELLS}"

    # rationale: one item per source paper, up to 5. The claim text here is a placeholder;
    # the checker RE-RENDERS it canonically from the record, so nothing here is forgeable.
    papers = prior.get("papers", [])[:5]
    rationale: list[RationaleItem] = []
    for p in papers:
        aid = str(p["activity_id"])
        doc = p.get("document_chembl_id")
        rationale.append(RationaleItem(
            claim="",  # checker fills this from the record
            pmid="",
            evidence_type="chembl_activity",
            evidence_id=aid,
            quote=None,
            status="unverified",  # the checker promotes to 'verified' if the id matches
            # link the source PAPER (ChEMBL document report card), not the activity page,
            # so a citation opens its paper with title + DOI.
            url=chembl_document_url(doc) or source_url(SourceType.CHEMBL_ACTIVITY, aid),  # B1.6
            document_chembl_id=doc,
        ))

    notes: list[str] = []
    if capped:
        notes.append(f"top_nM capped at {_MAX_TOP_nM:g} nM (uncapped would exceed it)")

def design_experiment(
    topic_id: str,
    prior_median_nM: float = 120.0,
    prior: dict | None = None,
    target_chembl_id: str | None = None,
) -> ExperimentDesign:
    """Deterministic placeholder design covering the prior by ~2 log units each side.

    Data wiring (this task): when a real ChEMBL `prior` dict is supplied (from
    `pipeline.ingest.chembl.prior_ic50_nM`), its median/n/spread and activity-id source
    are used instead of the placeholder, so the starting IC50 guess traces to ChEMBL.
    The dilution range is recentred on the real median so it still spans the prior.

    Real (future) version: prompt the Designer LLM with the topic, top PubMed abstracts
    and this prior, parse its JSON into ExperimentDesign, then run the citation checker.
    """
    if prior:
        median_nM = float(prior.get("median_nM", prior_median_nM))
        activity_ids = prior.get("activity_ids") or []
        prior_model = PriorIC50(
            median_nM=median_nM,
            n_measurements=int(prior.get("n_measurements", 1)),
            spread_log10=float(prior.get("spread_log10", 0.68)),
            source=Source(
                type=SourceType.CHEMBL_ACTIVITY,
                id=str(activity_ids[0]) if activity_ids else (target_chembl_id or "chembl"),
            ),
        )
    else:
        median_nM = prior_median_nM
        prior_model = PriorIC50(
            median_nM=prior_median_nM,
            n_measurements=6,
            spread_log10=0.68,
            source=Source(type=SourceType.CHEMBL_ACTIVITY, id="placeholder"),
        )

    # top of the dilution series ~2 log10 units above the median (100x), 3-fold steps.
    top_nM = round(median_nM * 100.0, 3)

    design = ExperimentDesign(
        design_id=design_id,
        topic_id=target,
        assay=Assay(
            type="dose_response",
            readout="percent_activity",
            target_chembl_id=target_chembl_id or "CHEMBL0000",
            compound_chembl_id="CHEMBL0000",
        ),
        prior_ic50=prior_model,
        dilution=Dilution(top_nM=top_nM, factor=3, points=10),
        replicates=3,
        controls=Controls(positive_wells=4, negative_wells=4),
        plate=Plate(),
        volumes_uL=Volumes(transfer=50, diluent=100),
    )
