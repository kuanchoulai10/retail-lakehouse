"""Tests for K8sSettings."""

from bootstrap.configs import AppSettings, K8sSettings


def test_defaults():
    """Verify that K8sSettings has correct default values."""
    s = K8sSettings()
    assert s.namespace == "default"
    assert s.image == "localhost:5000/table-maintenance-jobs:latest"
    assert s.image_pull_policy == "Never"
    assert s.spark_version == "4.0.0"
    assert s.service_account == "spark-operator-spark"
    assert s.iceberg_jar.startswith("https://repo1.maven.org/")
    assert s.iceberg_aws_jar.startswith("https://repo1.maven.org/")


def test_env_nested_override(monkeypatch):
    """Verify that nested K8s env vars override K8sSettings via AppSettings."""
    monkeypatch.setenv("GLAC_K8S__NAMESPACE", "spark-jobs")
    s = AppSettings()
    assert s.k8s.namespace == "spark-jobs"
