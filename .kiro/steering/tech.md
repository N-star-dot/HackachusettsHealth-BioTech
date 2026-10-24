# Tech & conventions

## Stack
- **Backend:** Python 3.10+ (Opentrons pins <=3.13; install it in a 3.13 env for the real sim).
- **Models:** Pydantic v2 for contracts, numpy/scipy for the Monte Carlo, scikit-learn
  (`HistGradientBoostingClassifier`) for the momentum model.
- **API:** FastAPI + uvicorn.
- **Database:** SQLite (committed schema, gitignored data file). WAL mode for the parallel team.
- **Frontend:** dashboard in `frontend/` (owner C's choice).

## Commands
```bash
pip install --upgrade pip && pip install -e ".[dev]"   # setup
pip install -e ".[robot]"      # add the real Opentrons simulator (needs Python <=3.13)
python scripts/init_db.py      # create database/app.db + load the offline cache seed
INGEST_OFFLINE=1 python scripts/demo.py "your topic"   # end-to-end, offline
python scripts/seed_cache.py --online --topic "your topic"  # refresh seed from live APIs
python scripts/eval_metrics.py          # the reported metrics
python -m pytest -q                      # tests
uvicorn backend.api:app --reload         # API at http://127.0.0.1:8000/docs
```

## Opentrons gotchas (learned in testing)
- Opentrons 10.x **rejects OT-2 protocols**. Write for the **Flex**, deck slots like `D1`.
- A Flex protocol **must** declare a trash bin: `protocol.load_trash_bin("A3")`, or the
  simulator halts at the first tip drop. The compiler template bakes this in.
- If Open Targets is added later, release 26.09 renamed `knownDrugs` ->
  `drugAndClinicalCandidates`; older examples break.

## Data-source rules
- Cache every API response on first pull (`pipeline/ingest/http_cache.py`) so the demo
  runs offline. The cache key excludes auth params (`api_key`, `mailto`, `email`), so a
  keyless seed is a hit whether or not a key is set, and no secret lands in a seed file.
- `cached_get_json` supports `ttl_seconds` (stale entries refetch when online; default
  `None` = never expire) and an offline mode (`offline=True` or `INGEST_OFFLINE=1`): a
  cached request is served locally, an uncached one raises `OfflineCacheMiss` rather than
  hitting the network.
- Commit the offline cache seed under `database/seed/<source>.json`; `init_db` loads it.
  Regenerate real data with `scripts/seed_cache.py --online` (run once, then commit).
- Keys are optional; keyless works at lower rate limits. `.env` is loaded automatically
  (gitignored). Set `CONTACT_EMAIL` for the polite pool.
- **Do not use Google Scholar.** Its robots.txt disallows `/scholar` for all bots, automated
  access violates Google's terms, and the Hackachusetts rules bar submissions that violate
  contract rights.

## Style
- Numbers carry a `Source`, or live in a `simulated`-labelled block. The contract models enforce this.
- Deterministic where possible: pass an explicit `seed` to the Monte Carlo.
- ruff, line length 100.
