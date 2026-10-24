# Offline cache seed

These JSON files pre-populate the `api_cache` table so the demo runs **offline** from
a clean clone. `init_db` (and `database.load_seed`) load them on setup.

## Format
One file per source, named `<source>.json` (`openalex`, `pubmed`, `chembl`). The file
stem is the cache `source`. Each file is a JSON **list** of records:

```json
[
  { "request_key": "<exact key from http_cache._request_key>",
    "status_code": 200,
    "response": { "...": "raw API body as the client expects it" } }
]
```

- `request_key` must match exactly what `pipeline.ingest.http_cache._request_key(url, params)`
  produces for the call, or it won't be a cache hit. Compute it with that helper rather
  than hand-writing it.
- `status_code` is optional (defaults to 200).
- Loading is idempotent (upsert), so re-running `init_db` is safe.

## Provenance
The values committed here are a **small example seed** (demo topic:
"kinase inhibitors for liver fibrosis") so the repo stays light. They are placeholders,
not sourced results. Run `scripts/seed_cache.py` **online once** (Task 4) to overwrite
these with real OpenAlex / PubMed / ChEMBL responses; after that the demo runs offline
with every number tracing to a real source.
