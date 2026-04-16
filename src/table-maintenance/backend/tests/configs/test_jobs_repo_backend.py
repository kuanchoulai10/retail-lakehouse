from configs import AppSettings, JobsRepoBackend


def test_enum_values():
    assert JobsRepoBackend.POSTGRES == "postgres"
    assert JobsRepoBackend.SQLITE == "sqlite"
    assert JobsRepoBackend.IN_MEMORY == "in_memory"


def test_app_settings_default_is_in_memory():
    s = AppSettings()
    assert s.jobs_repo_backend == JobsRepoBackend.IN_MEMORY


def test_app_settings_env_override(monkeypatch):
    monkeypatch.setenv("BACKEND_JOBS_REPO_BACKEND", "postgres")
    s = AppSettings()
    assert s.jobs_repo_backend == JobsRepoBackend.POSTGRES
