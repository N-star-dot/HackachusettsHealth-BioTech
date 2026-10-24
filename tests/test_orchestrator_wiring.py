"""Task 6: the orchestrator/stage-1 data flow reads real (seeded) sources offline.

Proves stage 1 produces OpenAlex-sourced counts from the cache (not placeholders) and
that citation verification stays conservative (unverified) when a PMID isn't cached.
"""

from __future__ import annotations

import pytest

import database.db as dbmod
import pipeline.ingest.http_cache as hc
from backend.stage1_topic.scoring import _counts_from_source
from backend.stage2_design import check_citations, design_experiment
from database.db import Database


@pytest.fixture
def seeded_db(tmp_path, monkeypatch):
    """A temp DB seeded with a self-consistent OpenAlex topic + works pair."""
    db = Database(tmp_path / "wire.db")
    monkeypatch.setattr(dbmod, "_singleton", db, raising=False)

    query = "kinase inhibitors for liver fibrosis"
    topic_id = "T99999"
    topics_key = hc._request_key(
        "https://api.openalex.org/topics", {"search": query, "per-page": 10}
    )
    works_key = hc._request_key(
        "https://api.openalex.org/works",
        {
            "filter": f"topics.id:{topic_id},from_publication_date:2015-01-01,"
                      f"to_publication_date:2024-12-31",
            "group_by": "publication_year",
        },
    )
    db.cache_put("openalex", topics_key, {"results": [
        {"id": f"https://openalex.org/{topic_id}", "display_name": "Kinases & Fibrosis",
         "works_count": 4120},
    ]})
    db.cache_put("openalex", works_key, {"group_by": [
        {"key": "2019", "count": 812}, {"key": "2020", "count": 905},
    ]})
    monkeypatch.setenv("INGEST_OFFLINE", "1")
    yield db, query, topic_id
    db.close()


def test_stage1_counts_come_from_seeded_openalex(seeded_db):
    _, query, topic_id = seeded_db
    topic, counts = _counts_from_source(query)
    assert topic.openalex_id == topic_id          # real id from the search hit
    assert topic.name == "Kinases & Fibrosis"
    assert [c.year for c in counts] == [2019, 2020]  # real seeded counts, not placeholder
    assert counts[0].works == 812
    assert counts[0].source.id == topic_id           # every count traces to the source


def test_stage1_falls_back_when_source_empty(tmp_path, monkeypatch):
    """No seed + offline -> OpenAlex miss raises, caught, placeholder counts returned."""
    db = Database(tmp_path / "empty.db")
    monkeypatch.setattr(dbmod, "_singleton", db, raising=False)
    monkeypatch.setenv("INGEST_OFFLINE", "1")
    topic, counts = _counts_from_source("some uncached topic")
    assert topic.openalex_id == "T00000"            # placeholder fallback
    assert len(counts) == 10                         # full placeholder series
    db.close()


def test_citation_check_unverified_when_pmid_uncached(seeded_db):
    """Offline, the stub's fake PMID can't resolve, so it stays unverified."""
    from pipeline.orchestrator import _safe_title_lookup

    design = design_experiment("T99999")
    checked = check_citations(design, lookup_title=_safe_title_lookup)
    assert all(not r.verified for r in checked.rationale)


def test_design_uses_real_chembl_prior():
    """A supplied ChEMBL prior flows into the design and recentres the dilution."""
    prior = {"median_nM": 50.0, "n_measurements": 12, "spread_log10": 0.5,
             "activity_ids": [987654]}
    design = design_experiment("T1", prior=prior, target_chembl_id="CHEMBL203")
    assert design.prior_ic50.median_nM == 50.0
    assert design.prior_ic50.n_measurements == 12
    assert design.prior_ic50.source.id == "987654"      # traces to a ChEMBL activity id
    assert design.assay.target_chembl_id == "CHEMBL203"
    assert design.dilution.top_nM == 5000.0              # 100x the real median
