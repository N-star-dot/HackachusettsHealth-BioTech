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
from backend.contracts.common import SourceType, source_url
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
            url=source_url(SourceType.CHEMBL_ACTIVITY, aid),  # B1.6
            document_chembl_id=doc,
        ))

    notes: list[str] = []
    if capped:
        notes.append(f"top_nM capped at {_MAX_TOP_nM:g} nM (uncapped would exceed it)")

    # B1.1: volumes must realise the dilution factor; derive diluent from it.
    transfer_uL = 50.0
    diluent_uL = transfer_uL * (dilution.factor - 1.0)

    design = ExperimentDesign(
        design_id=design_id,
        topic_id=target,
        assay=Assay(
            type="dose_response",
            readout="percent_activity",
            target_chembl_id=target,
            compound_chembl_id=compound,
        ),
        prior_ic50=PriorIC50(
            median_nM=median_nM,
            n_measurements=int(prior.get("n_papers", len(papers)) or 1),
            spread_log10=spread,
            source=Source(
                type=SourceType.CHEMBL_ACTIVITY,
                id=(_prior_ids := ",".join(str(a) for a in prior.get("activity_ids", [])[:10]) or "none"),
                url=source_url(SourceType.CHEMBL_ACTIVITY, _prior_ids),
            ),
        ),
        dilution=dilution,
        replicates=replicates,
        controls=controls,
        plate=Plate(labware="corning_96_wellplate_360ul_flat", layout="rows"),
        volumes_uL=Volumes(transfer=transfer_uL, diluent=diluent_uL),
        pipette="flex_1channel_1000",
        tiprack="opentrons_flex_96_tiprack_200ul",
        rationale=rationale,
        notes=notes,
    )
    return design


def design_experiment(topic_id: str | None = None, compound_chembl_id: str | None = None,
                      design_id: str = "d-001") -> ExperimentDesign:
    """Entry point. Loads a demo pair (by compound id, default the first) and builds a
    deterministic design. Falls back to a minimal placeholder only if no demo data exists."""
    pair = get_demo_pair(compound_chembl_id)
    if pair is not None:
        return design_from_pair(pair, design_id=design_id)

    # last-resort placeholder (no demo data on disk) — keeps the stage from crashing
    return ExperimentDesign(
        design_id=design_id,
        topic_id=topic_id or "unknown",
        assay=Assay(target_chembl_id="CHEMBL0000", compound_chembl_id="CHEMBL0000"),
        prior_ic50=PriorIC50(median_nM=120.0, n_measurements=1, spread_log10=0.68,
                             source=Source(type=SourceType.CHEMBL_ACTIVITY, id="none")),
        dilution=Dilution(top_nM=12000, factor=3, points=10),
        replicates=3,
        controls=Controls(positive_wells=4, negative_wells=4),
        plate=Plate(),
        volumes_uL=Volumes(transfer=50, diluent=100),
    )
