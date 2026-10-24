"""Parsing/normalization tests for the ingest clients (Task 2).

These hit the `_parse_*` helpers directly with fixture payloads — no network and no
cache — to prove the clients fail soft on malformed, empty, and partial responses.
"""

from __future__ import annotations

from pipeline.ingest import chembl, openalex, pubmed


# --- OpenAlex -----------------------------------------------------------------
def test_openalex_works_by_year_sorted_and_coerced():
    body = {"group_by": [
        {"key": "2021", "count": "1010"},
        {"key": "2019", "count": 812},
    ]}
    out = openalex._parse_works_by_year(body)
    assert out == [{"year": 2019, "works": 812}, {"year": 2021, "works": 1010}]


def test_openalex_works_by_year_skips_bad_rows():
    body = {"group_by": [
        {"key": "2020", "count": 900},
        {"key": "not-a-year", "count": 5},   # bad key
        {"count": 5},                          # missing key
        "garbage",                             # not a dict
    ]}
    out = openalex._parse_works_by_year(body)
    assert out == [{"year": 2020, "works": 900}]


def test_openalex_works_by_year_empty_on_odd_body():
    assert openalex._parse_works_by_year({}) == []
    assert openalex._parse_works_by_year(None) == []
    assert openalex._parse_works_by_year({"group_by": None}) == []


def test_openalex_topics_normalized():
    body = {"results": [
        {"id": "T1", "display_name": "Kinases", "works_count": "340"},
        {"display_name": "no id"},   # dropped: no id
        {"id": "T2"},                # works_count defaults to 0
    ]}
    out = openalex._parse_topics(body)
    assert out == [
        {"id": "T1", "display_name": "Kinases", "works_count": 340},
        {"id": "T2", "display_name": "", "works_count": 0},
    ]


# --- PubMed -------------------------------------------------------------------
def test_pubmed_title_found():
    body = {"result": {"123": {"title": "A paper"}}}
    assert pubmed._parse_title(body, "123") == "A paper"


def test_pubmed_title_missing_or_error():
    assert pubmed._parse_title({"result": {"123": {"error": "not found"}}}, "123") is None
    assert pubmed._parse_title({"result": {}}, "123") is None
    assert pubmed._parse_title({}, "123") is None
    assert pubmed._parse_title(None, "123") is None
    assert pubmed._parse_title({"result": {"123": {"title": ""}}}, "123") is None


def test_pubmed_pmids_deduped_order_preserved():
    body = {"esearchresult": {"idlist": ["9", "3", "9", "7"]}}
    assert pubmed._parse_pmids(body) == ["9", "3", "7"]


def test_pubmed_pmids_empty_on_odd_body():
    assert pubmed._parse_pmids({}) == []
    assert pubmed._parse_pmids(None) == []
    assert pubmed._parse_pmids({"esearchresult": None}) == []


# --- ChEMBL -------------------------------------------------------------------
def test_chembl_activities_coerced_and_filtered():
    body = {"activities": [
        {"activity_id": 1, "standard_value": "120.0"},
        {"activity_id": 2, "standard_value": -5},        # dropped: non-positive
        {"activity_id": 3, "standard_value": "nope"},    # dropped: non-numeric
        {"activity_id": 4, "standard_value": None},      # dropped: missing
        {"activity_id": 5, "standard_value": 80},
        "garbage",                                        # dropped: not a dict
    ]}
    out = chembl._parse_activities(body)
    assert [a["activity_id"] for a in out] == [1, 5]
    assert out[0]["standard_value_nM"] == 120.0
    assert isinstance(out[0]["standard_value_nM"], float)


def test_chembl_activities_empty_on_odd_body():
    assert chembl._parse_activities({}) == []
    assert chembl._parse_activities(None) == []
    assert chembl._parse_activities({"activities": None}) == []
