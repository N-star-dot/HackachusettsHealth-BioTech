"""Tests for the .env loader (API keys / CONTACT_EMAIL). No secrets are committed."""

from __future__ import annotations

import os

import pytest

from pipeline.ingest import env as envmod


@pytest.fixture(autouse=True)
def _restore_environ():
    """load_env writes to os.environ directly; snapshot and restore so these tests
    never leak API-key values into other tests."""
    saved = dict(os.environ)
    yield
    os.environ.clear()
    os.environ.update(saved)


def _write_env(tmp_path, body: str):
    p = tmp_path / ".env"
    p.write_text(body)
    return p


def test_load_env_sets_values(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENALEX_API_KEY", raising=False)
    env_path = _write_env(tmp_path, "OPENALEX_API_KEY=abc123\nCONTACT_EMAIL=me@example.com\n")
    assert envmod.load_env(env_path) is True
    import os
    assert os.environ["OPENALEX_API_KEY"] == "abc123"
    assert os.environ["CONTACT_EMAIL"] == "me@example.com"


def test_load_env_does_not_override_existing(tmp_path, monkeypatch):
    monkeypatch.setenv("NCBI_API_KEY", "from-shell")
    env_path = _write_env(tmp_path, "NCBI_API_KEY=from-file\n")
    envmod.load_env(env_path)
    import os
    assert os.environ["NCBI_API_KEY"] == "from-shell"  # shell wins


def test_load_env_override_true(tmp_path, monkeypatch):
    monkeypatch.setenv("NCBI_API_KEY", "from-shell")
    env_path = _write_env(tmp_path, "NCBI_API_KEY=from-file\n")
    envmod.load_env(env_path, override=True)
    import os
    assert os.environ["NCBI_API_KEY"] == "from-file"


def test_load_env_missing_file_is_noop(tmp_path):
    assert envmod.load_env(tmp_path / "nope.env") is False


def test_fallback_parser(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENALEX_API_KEY", raising=False)
    env_path = _write_env(
        tmp_path,
        "# a comment\n\nOPENALEX_API_KEY=\"quoted-value\"\nIGNORED_NO_EQUALS\n",
    )
    envmod._load_env_fallback(env_path, override=False)
    import os
    assert os.environ["OPENALEX_API_KEY"] == "quoted-value"
