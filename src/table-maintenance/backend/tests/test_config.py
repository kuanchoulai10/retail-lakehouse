from config import AppSettings


def test_defaults():
    s = AppSettings()
    assert s.namespace == "default"
    assert s.image == "localhost:5000/table-maintenance-jobs:latest"
    assert s.image_pull_policy == "Never"
    assert s.spark_version == "4.0.0"
    assert s.service_account == "spark-operator-spark"


def test_env_override(monkeypatch):
    monkeypatch.setenv("BACKEND_NAMESPACE", "spark-jobs")
    s = AppSettings()
    assert s.namespace == "spark-jobs"
