"""Single source of truth for every noise level, each tagged with a real Source.

Biology dominates: the lab-to-lab IC50 spread (~2.7-fold) dwarfs robot pipetting
error, except at the smallest transfer volumes, which the planner avoids.

Pipette numbers are the PUBLISHED Opentrons Flex values (B0.7), page
https://docs.opentrons.com/flex/system-description/pipettes/ (checked 2026-10-24), so the
dashboard popover that cites "Opentrons spec" is actually correct.
"""

from __future__ import annotations

from backend.contracts.common import Source, SourceType

# Kalliokoski 2013, >16,000 ChEMBL IC50 measurement pairs.
# Median gap 0.43 log units (~2.7-fold); spread 0.68 log units.
LAB_SPREAD_LOG10 = 0.68
KALLIOKOSKI_DOI = "10.1371/journal.pone.0061007"

_SPEC_URL = "https://docs.opentrons.com/flex/system-description/pipettes/"

# Published Flex pipette accuracy. Per pipette: its working range (min, max µL) and a list
# of measured points (transfer_volume_uL, random_cv, systematic_bias), ascending by volume.
# We pick the nearest listed point AT OR BELOW the transfer volume. Transfers below the
# pipette's minimum are rejected (ValueError -> 422 at the API).
_PIPETTE_SPEC: dict[str, dict] = {
    # Flex 1-Channel 1000 µL, range 5-1000 µL
    "flex_1channel_1000": {
        "range": (5.0, 1000.0),
        "points": [
            (5.0, 0.0250, 0.0500),
            (50.0, 0.0030, 0.0050),
            (200.0, 0.0015, 0.0050),
            (1000.0, 0.0015, 0.0050),
        ],
    },
    "flex_8channel_1000": {
        "range": (5.0, 1000.0),
        "points": [
            (5.0, 0.0250, 0.0500),
            (50.0, 0.0030, 0.0050),
            (200.0, 0.0015, 0.0050),
            (1000.0, 0.0015, 0.0050),
        ],
    },
    # Flex 1-Channel 50 µL, range 1-50 µL
    "flex_1channel_50": {
        "range": (1.0, 50.0),
        "points": [
            (1.0, 0.0700, 0.0800),   # 50 µL tip moving 1 µL (worst case)
            (5.0, 0.0075, 0.0150),
            (10.0, 0.0050, 0.0150),
            (50.0, 0.0040, 0.0125),
        ],
    },
}

_DEFAULT_PIPETTE = "flex_1channel_1000"


def _nearest_point(points: list[tuple[float, float, float]], volume_uL: float) -> tuple[float, float, float]:
    """The listed point with the largest volume <= volume_uL (first point if below all)."""
    chosen = points[0]
    for v, cv, bias in points:
        if volume_uL >= v:
            chosen = (v, cv, bias)
    return chosen


def lookup_pipette_error(pipette: str, volume_uL: float) -> tuple[float, float]:
    """Return (random_cv, systematic_bias) for a pipette moving `volume_uL`.

    Raises ValueError if the volume is below the pipette's minimum (the dashboard should
    never send that; enforced in the browser, and 422'd by the API if it does).
    """
    spec = _PIPETTE_SPEC.get(pipette, _PIPETTE_SPEC[_DEFAULT_PIPETTE])
    lo, _hi = spec["range"]
    if volume_uL < lo:
        raise ValueError(
            f"{pipette} cannot move {volume_uL} µL; its minimum is {lo} µL"
        )
    _v, cv, bias = _nearest_point(spec["points"], volume_uL)
    return cv, bias


def pipette_spec_source(pipette: str, volume_uL: float) -> Source:
    """The Opentrons-spec Source for a pipette/volume, naming the nearest published point."""
    spec = _PIPETTE_SPEC.get(pipette, _PIPETTE_SPEC[_DEFAULT_PIPETTE])
    v, _cv, _bias = _nearest_point(spec["points"], volume_uL)
    return Source(type=SourceType.SPEC,
                  id=f"{pipette}, nearest published point {v:g} µL", url=_SPEC_URL)


def kalliokoski_source() -> Source:
    return Source(type=SourceType.PAPER, id=f"doi:{KALLIOKOSKI_DOI}",
                  url=f"https://doi.org/{KALLIOKOSKI_DOI}")


def noise_sources() -> list[Source]:
    return [
        kalliokoski_source(),
        Source(type=SourceType.SPEC, id="opentrons-flex-pipettes", url=_SPEC_URL),
    ]
