from configs import AppSettings, SqliteSettings


def test_defaults():
    s = SqliteSettings()
    assert s.db_path == ":memory:"


def test_env_nested_override(monkeypatch):
    monkeypatch.setenv("BACKEND_SQLITE__DB_PATH", "/tmp/jobs.db")
    s = AppSettings()
    assert s.sqlite.db_path == "/tmp/jobs.db"
