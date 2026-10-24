-- SQLite schema for HackachusettsHealth-BioTech.
-- Two jobs: (1) cache every external API response so the demo runs offline,
-- (2) persist the JSON reports each stage produces so the dashboard can reload runs.
--
-- Design notes:
--   * Reports are stored as JSON blobs keyed by stage + id. We validate them with
--     Pydantic on the way in/out, so the DB stays schema-light and resilient to
--     contract tweaks during the hackathon.
--   * The api_cache table is a generic key/value store keyed by (source, request_key)
--     with a fetched_at timestamp so the pipeline can honour TTLs.

PRAGMA journal_mode = WAL;        -- better concurrency for the parallel team
PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------------
-- 1. External API response cache (owned by the pipeline / ingest workstream)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS api_cache (
    source       TEXT NOT NULL,              -- 'openalex' | 'pubmed' | 'chembl' | 'semantic_scholar'
    request_key  TEXT NOT NULL,              -- normalised request (e.g. endpoint + sorted params)
    response     TEXT NOT NULL,              -- raw JSON body as returned by the API
    status_code  INTEGER NOT NULL DEFAULT 200,
    fetched_at   TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (source, request_key)
);
CREATE INDEX IF NOT EXISTS idx_api_cache_source ON api_cache(source);

-- ---------------------------------------------------------------------------
-- 2. A "run" ties the five stages together for one researcher query
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS runs (
    run_id      TEXT PRIMARY KEY,            -- uuid
    query       TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    status      TEXT NOT NULL DEFAULT 'started'  -- started | topic | design | sim | uncertainty | done | error
);

-- ---------------------------------------------------------------------------
-- 3. Stage outputs, one row per (run, stage). Validated JSON contracts.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS reports (
    run_id      TEXT NOT NULL,
    stage       TEXT NOT NULL,               -- 'topic' | 'design' | 'sim' | 'uncertainty'
    payload     TEXT NOT NULL,               -- the contract JSON
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (run_id, stage),
    FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
);

-- ---------------------------------------------------------------------------
-- 4. Momentum model training cache (owned by A) — topic features/labels so the
--    model can be retrained without re-pulling 2,000 OpenAlex topics each time.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS topic_features (
    openalex_id TEXT PRIMARY KEY,
    name        TEXT,
    features    TEXT NOT NULL,               -- JSON feature vector (counts up to 2019 only)
    label       INTEGER,                     -- 1 if grew faster than median 2020-2024, else 0, null if unknown
    growth      REAL,                        -- raw 2020-2024 log10 growth slope (for top-decile eval; NOT a feature)
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ---------------------------------------------------------------------------
-- 5. Calibration groups (owned by A) — real ChEMBL IC50 measurement groups per
--    (target, compound) pair with >=3 values. The uncertainty engine holds one
--    value out and checks whether its 90% interval covers it.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS calibration_groups (
    target_chembl_id   TEXT NOT NULL,
    molecule_chembl_id TEXT NOT NULL,
    values_nM          TEXT NOT NULL,        -- JSON list of IC50 values (nM), >=3 of them
    activity_ids       TEXT NOT NULL,        -- JSON list of ChEMBL activity ids (provenance)
    updated_at         TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (target_chembl_id, molecule_chembl_id)
);
