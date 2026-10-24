"""B0.7: pipette error table matches the published Opentrons spec."""

from __future__ import annotations

import pytest

from backend.stage4_uncertainty.noise_sources import (
    lookup_pipette_error,
    pipette_spec_source,
)


def test_flex_1000_at_50uL_matches_spec():
    cv, bias = lookup_pipette_error("flex_1channel_1000", 50)
    assert cv == 0.003 and bias == 0.005


def test_nearest_point_at_or_below():
    # 120 µL -> nearest listed point at/below is 50 µL for the 1000 µL pipette
    cv, bias = lookup_pipette_error("flex_1channel_1000", 120)
    assert cv == 0.003 and bias == 0.005
    # 250 µL -> 200 µL point
    cv2, _ = lookup_pipette_error("flex_1channel_1000", 250)
    assert cv2 == 0.0015


def test_below_minimum_raises():
    with pytest.raises(ValueError):
        lookup_pipette_error("flex_1channel_1000", 2)  # below the 5 µL minimum


def test_small_pipette_1uL_worst_case():
    cv, bias = lookup_pipette_error("flex_1channel_50", 1)
    assert cv == 0.07 and bias == 0.08


def test_spec_source_names_point_and_url():
    src = pipette_spec_source("flex_1channel_1000", 50)
    assert src.type.value == "spec"
    assert "50" in src.id
    assert "opentrons.com" in (src.url or "")
