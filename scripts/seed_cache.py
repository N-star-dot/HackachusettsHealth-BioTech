"""Generate the offline cache seed from a one-time online pull.

Two phases, so the network step is explicit and separable:

  1. pull   — run the demo topic through the OpenAlex / PubMed / ChEMBL clients so
              their real responses land in api_cache. REQUIRES NETWORK (and uses any
              API keys / CONTACT_EMAIL from the environment). Only runs with --online.
  2. export — read api_cache rows and write database/seed/<source>.json in the format
              database.load_seed expects. No network.

Typical use (run once, online, then commit the seed):

    python scripts/seed_cache.py --online --topic "kinase inhibitors for liver fibrosis"

Export only (no network — regenerate seed files from an already-warm DB):

    python scripts/seed_cache.py

After committing database/seed/*.json, the demo runs fully offline:

    INGEST_OFFLINE=1 python scripts/demo.py "kinase inhibitors for liver fibrosis"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from database import get_db
from database.db import _SEED_DIR

# Sources we export. Keep in sync with the ingest clients.
_SOURCES = ("openalex", "pubmed", "chembl")

_DEMO_TOPIC = "kinase inhibitors for liver fibrosis"


def pull_topic(topic: str) -> None:
    """Make the real API calls for `topic` so responses populate api_cache.

    Imported lazily so `export` works without httpx/network side effects. Each call
    is wrapped so one failing source doesn't abort the others.
    """
    from pipeline.ingest import chembl, openalex, pubmed
    from pipeline.ingest.env import load_env

    load_env()  # pick up API keys / CONTACT_EMAIL from a local .env (optional)

    print(f"[pull] OpenAlex: searching topics for {topic!r}")
    topics = openalex.search_topics(topic)
    if topics:
        top_id = topics[0]["id"]
        print(f"[pull] OpenAlex: works-by-year for {top_id}")
        openalex.works_by_year(top_id)
    else:
        print("[pull] OpenAlex: no topics returned; skipping works-by-year")

    print(f"[pull] PubMed: searching abstracts for {topic!r}")
    pmids = pubmed.search(topic, retmax=5)
    for pmid in pmids:
        print(f"[pull] PubMed: title for PMID {pmid}")
        pubmed.fetch_title(pmid)

    # A representative target for the stage-2 prior + stage-4 calibration.
    target = "CHEMBL203"  # EGFR; commonly used kinase target with many IC50 rows
    print(f"[pull] ChEMBL: IC50 activities for {target}")
    chembl.ic50_activities(target)


def export_seed(seed_dir: Path) -> int:
    """Write api_cache rows to seed_dir/<source>.json. Returns rows exported."""
    db = get_db()
    seed_dir.mkdir(parents=True, exist_ok=True)
    total = 0
    for source in _SOURCES:
        rows = db.cache_all(source)
        records = [
            {"request_key": r["request_key"], "status_code": r["status_code"],
             "response": r["response"]}
            for r in rows
        ]
        out_path = seed_dir / f"{source}.json"
        out_path.write_text(json.dumps(records, indent=2) + "\n")
        print(f"[export] {source}: {len(records)} record(s) -> {out_path}")
        total += len(records)
    return total


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the offline cache seed.")
    parser.add_argument("--online", action="store_true",
                        help="Make live API calls to populate the cache (needs network).")
    parser.add_argument("--topic", default=_DEMO_TOPIC, help="Topic to pull.")
    parser.add_argument("--seed-dir", default=str(_SEED_DIR), help="Output seed directory.")
    args = parser.parse_args()

    if args.online:
        print("=== PULL (online) ===")
        print("This makes live requests to OpenAlex, PubMed, and ChEMBL.")
        pull_topic(args.topic)
    else:
        print("=== export-only (no network); pass --online to refresh from the APIs) ===")

    print("=== EXPORT ===")
    total = export_seed(Path(args.seed_dir))
    print(f"\nWrote {total} cached response(s) to {args.seed_dir}.")
    if total == 0:
        print("Nothing to export. Run with --online first to populate the cache.",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
