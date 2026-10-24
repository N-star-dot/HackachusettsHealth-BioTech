"""init_db auto-seeding (Task 5)."""

from __future__ import annotations

from database import init_db


def test_init_db_seeds_by_default(tmp_path):
    db = init_db(tmp_path / "seeded.db")  # seed=True default -> loads database/seed/
    try:
        rows = db.cache_all()
        assert len(rows) >= 1  # committed seed has at least the OpenAlex entries
    finally:
        db.close()


def test_init_db_no_seed(tmp_path):
    db = init_db(tmp_path / "empty.db", seed=False)
    try:
        assert db.cache_all() == []
    finally:
        db.close()
