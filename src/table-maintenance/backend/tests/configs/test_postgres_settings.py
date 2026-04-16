from configs import AppSettings, PostgresSettings


def test_defaults():
    s = PostgresSettings()
    assert s.db_url == ""
    assert s.pool_size == 5


def test_env_nested_override(monkeypatch):
    monkeypatch.setenv("BACKEND_POSTGRES__DB_URL", "postgresql://localhost/jobs")
    monkeypatch.setenv("BACKEND_POSTGRES__POOL_SIZE", "10")
    s = AppSettings()
    assert s.postgres.db_url == "postgresql://localhost/jobs"
    assert s.postgres.pool_size == 10
