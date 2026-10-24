"""Stage 2: experiment design. Owner B.

The Designer LLM writes an ExperimentDesign as JSON (never code). The citation
checker verifies every PubMed id. This stub returns a deterministic, valid design so
downstream stages work offline; wire `design_experiment` to the LLM when the key is
set (see designer_llm docstring below).
"""

from __future__ import annotations

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
from backend.contracts.common import SourceType


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
        design_id="d-001",
        topic_id=topic_id,
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
        plate=Plate(labware="corning_96_wellplate_360ul_flat", layout="randomized"),
        volumes_uL=Volumes(transfer=50, diluent=100),
        pipette="flex_1channel_1000",
        tiprack="opentrons_flex_96_tiprack_200ul",
        rationale=[RationaleItem(claim="placeholder claim", pmid="00000000", verified=False)],
    )
    return design
