"""Tests for PostgresSettings."""

from bootstrap.configs import AppSettings, PostgresSettings


def test_defaults():
    """Verify that PostgresSettings has correct default values."""
    s = PostgresSettings()
    assert s.db_url == ""
    assert s.pool_size == 5


def test_env_nested_override(monkeypatch):
    """Verify that nested Postgres env vars override PostgresSettings via AppSettings."""
    monkeypatch.setenv("GLAC_POSTGRES__DB_URL", "postgresql://localhost/jobs")
    monkeypatch.setenv("GLAC_POSTGRES__POOL_SIZE", "10")
    s = AppSettings()
    assert s.postgres.db_url == "postgresql://localhost/jobs"
    assert s.postgres.pool_size == 10
