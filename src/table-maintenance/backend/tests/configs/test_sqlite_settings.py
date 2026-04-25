"""Tests for SqliteSettings."""

from core.configs import AppSettings, SqliteSettings


def test_defaults():
    """Verify that SqliteSettings defaults to in-memory database."""
    s = SqliteSettings()
    assert s.db_path == ":memory:"


def test_env_nested_override(monkeypatch):
    """Verify that nested SQLite env vars override SqliteSettings via AppSettings."""
    monkeypatch.setenv("BACKEND_SQLITE__DB_PATH", "/tmp/jobs.db")
    s = AppSettings()
    assert s.sqlite.db_path == "/tmp/jobs.db"
