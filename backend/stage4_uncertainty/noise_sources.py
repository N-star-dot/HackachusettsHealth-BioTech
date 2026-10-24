"""Single source of truth for every noise level, each tagged with a real Source.

Biology dominates: the lab-to-lab IC50 spread (~2.7-fold) dwarfs robot pipetting
error (1%-10%), except at 1 µL transfers, which the planner avoids.
"""

from __future__ import annotations

from backend.contracts.common import Source, SourceType

# Kalliokoski 2013, >16,000 ChEMBL IC50 measurement pairs.
# Median gap 0.43 log units (~2.7-fold); spread 0.68 log units.
LAB_SPREAD_LOG10 = 0.68
KALLIOKOSKI_DOI = "10.1371/journal.pone.0061007"

# Opentrons Flex pipette spec table: (random CV, max systematic bias) per regime.
# Keyed by (pipette family, volume band). Values from Opentrons' published specs.
# 50 µL moving 50 µL  -> 0.40% random, up to 1.25% bias.
# 50 µL moving 1 µL   -> 7.00% random, up to 8.00% bias  (the regime to avoid).
_PIPETTE_SPEC: dict[str, list[tuple[float, float, float]]] = {
    # family: list of (min_volume_uL_inclusive, random_cv, bias) sorted ascending
    "flex_1channel_50": [
        (1.0, 0.07, 0.08),   # 1 µL: large error
        (5.0, 0.015, 0.02),  # mid
        (25.0, 0.004, 0.0125),  # near full
    ],
    "flex_1channel_1000": [
        (1.0, 0.05, 0.06),
        (10.0, 0.01, 0.015),
        (100.0, 0.003, 0.005),
    ],
    "flex_8channel_1000": [
        (1.0, 0.05, 0.06),
        (10.0, 0.01, 0.015),
        (100.0, 0.003, 0.005),
    ],
}


def lookup_pipette_error(pipette: str, volume_uL: float) -> tuple[float, float]:
    """Return (random_cv, systematic_bias) for a pipette moving `volume_uL`.

    Falls back to the flex_1channel_1000 table if the pipette is unknown, and to the
    lowest band if the volume is below the smallest listed.
    """
    bands = _PIPETTE_SPEC.get(pipette, _PIPETTE_SPEC["flex_1channel_1000"])
    chosen = bands[0]
    for min_v, cv, bias in bands:
        if volume_uL >= min_v:
            chosen = (min_v, cv, bias)
    return chosen[1], chosen[2]


def noise_sources() -> list[Source]:
    return [
        Source(type=SourceType.PAPER, id=f"doi:{KALLIOKOSKI_DOI}",
               url=f"https://doi.org/{KALLIOKOSKI_DOI}"),
        Source(type=SourceType.SPEC, id="opentrons-flex-pipettes"),
    ]
