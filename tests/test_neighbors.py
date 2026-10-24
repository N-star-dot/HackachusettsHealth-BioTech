"""B2.2: real neighbors (shift to a less explored topic)."""

from __future__ import annotations

from backend.stage1_topic import score_topic


def test_neighbors_are_real_not_placeholder():
    r = score_topic("HER2 kinase inhibitors in breast cancer")
    # never the old placeholder
    assert all(n.openalex_id != "T00001" for n in r.neighbors)
    assert all(not n.name.lower().startswith("placeholder") for n in r.neighbors)
    # if any resolved, they are less crowded than the query topic and carry a works count
    this_total = sum(c.works for c in r.counts_by_year if 2020 <= c.year <= 2024)
    for n in r.neighbors:
        assert n.works_last_5y < this_total
        assert n.works_last_5y >= 0


def test_offline_topic_has_no_neighbors(monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("down")

    monkeypatch.setattr("pipeline.ingest.openalex.search_works_group_by_topic", _boom)
    monkeypatch.setattr("pipeline.ingest.openalex.search_topics", _boom)
    r = score_topic("some benign kinase topic")
    assert r.neighbors == []
