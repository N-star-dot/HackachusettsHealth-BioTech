"""Create the SQLite database, apply the schema, and load the offline cache seed.

    python scripts/init_db.py

Seeding pours the committed database/seed/*.json into api_cache so the pipeline can
run offline from a clean clone. Pass --no-seed to create an empty database instead.
"""

from __future__ import annotations

import argparse

from database import init_db


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialise the local database.")
    parser.add_argument("--no-seed", action="store_true",
                        help="Create the database without loading the offline cache seed.")
    args = parser.parse_args()

    db = init_db(seed=not args.no_seed)
    print(f"Initialised database at {db.path}")

    if args.no_seed:
        print("Skipped seeding (--no-seed).")
    else:
        # idempotent re-load just to report how many cached responses are present
        seeded = db.load_seed()
        print(f"Loaded {seeded} cached response(s) from the offline seed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
