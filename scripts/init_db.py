"""Create the SQLite database and apply the schema.

    python scripts/init_db.py
"""

from __future__ import annotations

from database import init_db


def main() -> int:
    db = init_db()
    print(f"Initialised database at {db.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
