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


def design_experiment(topic_id: str, prior_median_nM: float = 120.0) -> ExperimentDesign:
    """Deterministic placeholder design covering the prior by ~2 log units each side.

    Real version: prompt the Designer LLM with the topic, top PubMed abstracts and the
    ChEMBL prior, parse its JSON into ExperimentDesign, then run the citation checker.
    """
    design = ExperimentDesign(
        design_id="d-001",
        topic_id=topic_id,
        assay=Assay(
            type="dose_response",
            readout="percent_activity",
            target_chembl_id="CHEMBL0000",
            compound_chembl_id="CHEMBL0000",
        ),
        prior_ic50=PriorIC50(
            median_nM=prior_median_nM,
            n_measurements=6,
            spread_log10=0.68,
            source=Source(type=SourceType.CHEMBL_ACTIVITY, id="placeholder"),
        ),
        dilution=Dilution(top_nM=12000, factor=3, points=10),
        replicates=3,
        controls=Controls(positive_wells=4, negative_wells=4),
        plate=Plate(labware="corning_96_wellplate_360ul_flat", layout="randomized"),
        volumes_uL=Volumes(transfer=50, diluent=100),
        pipette="flex_1channel_1000",
        tiprack="opentrons_flex_96_tiprack_200ul",
        rationale=[RationaleItem(claim="placeholder claim", pmid="00000000", verified=False)],
    )
    return design
