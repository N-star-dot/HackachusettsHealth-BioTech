"""B0.2: honest stage 1.

When OpenAlex is unreachable the report must say so: offline=True, placeholder counts
labelled 'simulated' (not openalex), no placeholder neighbors, and the four constant
axes carry an 'assumed' source.
"""

from __future__ import annotations

import pytest

from backend.stage1_topic import scoring


def test_offline_topic_is_honest(monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("openalex down")

    monkeypatch.setattr("pipeline.ingest.openalex.search_topics", _boom)

    report = scoring.score_topic("some benign kinase topic")

    assert report.offline is True
    assert report.momentum.model == "offline-placeholder"
    # every count source is simulated, never openalex
    assert all(c.source.type.value == "simulated" for c in report.counts_by_year)
    # no placeholder neighbors
    assert report.neighbors == []
    # the four constant axes are 'assumed'
    for axis in ("novelty", "evidence", "automatable", "cost_time"):
        assert report.matrix.axis_sources[axis].type.value == "assumed"


def test_online_topic_sources_momentum_to_openalex(monkeypatch):
    """When counts resolve, momentum's axis source is the OpenAlex counts url."""
    monkeypatch.setattr(
        "pipeline.ingest.openalex.search_topics",
        lambda q, per_page=1: [{"id": "https://openalex.org/T10966",
                                "display_name": "Liver physiology",
                                "field": {"display_name": "Medicine"}}],
    )
    monkeypatch.setattr(
        "pipeline.ingest.openalex.works_by_year",
        lambda oa_id, **k: [{"year": y, "works": 500 + y} for y in range(2015, 2025)],
    )
    report = scoring.score_topic("liver fibrosis")
    assert report.offline is False
    assert report.matrix.axis_sources["momentum"].type.value == "openalex"
    assert "api.openalex.org/works" in (report.matrix.axis_sources["momentum"].url or "")
