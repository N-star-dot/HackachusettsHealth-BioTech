"""Leakage guard: no 2020-2024 count may ever affect any 2015-2019 feature.

If changing a label-window count ever moved a feature, the model would be cheating.

There are two tests:
  * a Hypothesis property test (per the spec) that fuzzes the 2020-2024 window, and
  * a deterministic test that always runs, so the guard holds even where the installed
    Hypothesis build is incompatible with the interpreter (e.g. a broken engine on the
    very first 3.10.0 release).
"""

from __future__ import annotations

import random

import pytest

from backend.stage1_topic.features import FEATURE_YEARS, LABEL_YEARS, compute_features

_BASE_FEATURE_COUNTS = {y: 100 + i * 50 for i, y in enumerate(FEATURE_YEARS)}


def _features_for(label_counts: list[int]) -> dict:
    counts = [{"year": y, "works": _BASE_FEATURE_COUNTS[y]} for y in FEATURE_YEARS]
    counts += [{"year": y, "works": c} for y, c in zip(LABEL_YEARS, label_counts)]
    return compute_features(counts)


def test_label_window_never_affects_features_deterministic():
    """Always-on guard: 5000 random 2020-2024 perturbations change no feature."""
    rng = random.Random(0)
    ref = _features_for([0] * len(LABEL_YEARS))
    assert ref is not None
    for _ in range(5000):
        label_counts = [rng.randint(0, 10_000_000) for _ in LABEL_YEARS]
        assert _features_for(label_counts) == ref, "A 2020-2024 count changed a feature — leakage!"


# --- Hypothesis property test (skipped if the local Hypothesis engine is broken) ---
try:
    from hypothesis import given, settings
    from hypothesis import strategies as st

    _HAVE_HYP = True
except Exception:  # pragma: no cover
    _HAVE_HYP = False


@pytest.mark.skipif(not _HAVE_HYP, reason="hypothesis not installed")
def test_label_window_never_affects_features_property():
    @settings(max_examples=200, deadline=None)
    @given(
        a=st.lists(st.integers(0, 10_000_000), min_size=len(LABEL_YEARS), max_size=len(LABEL_YEARS)),
        b=st.lists(st.integers(0, 10_000_000), min_size=len(LABEL_YEARS), max_size=len(LABEL_YEARS)),
    )
    def _prop(a, b):
        assert _features_for(a) == _features_for(b), "2020-2024 counts changed a feature!"

    try:
        _prop()
    except AttributeError as exc:  # broken Hypothesis engine on this interpreter
        if "is_exhausted" in str(exc):
            pytest.skip(f"incompatible Hypothesis engine on this interpreter: {exc}")
        raise
