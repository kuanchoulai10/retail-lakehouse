"""Tests for AppSettings configuration."""

from bootstrap.configs import AppSettings
from bootstrap.configs.component import Component


def test_defaults():
    """Verify that AppSettings exposes correct K8sSettings defaults."""
    s = AppSettings()
    assert s.k8s.namespace == "default"
    assert s.k8s.image == "localhost:5000/table-maintenance-jobs:latest"
    assert s.k8s.image_pull_policy == "Never"
    assert s.k8s.spark_version == "4.0.0"
    assert s.k8s.service_account == "spark-operator-spark"
    assert s.k8s.driver_memory == "512m"
    assert s.k8s.executor_memory == "1g"
    assert s.k8s.executor_instances == 1


def test_env_nested_override(monkeypatch):
    """Verify that nested K8s env vars override AppSettings K8s sub-settings."""
    monkeypatch.setenv("GLAC_K8S__NAMESPACE", "spark-jobs")
    s = AppSettings()
    assert s.k8s.namespace == "spark-jobs"


def test_component_defaults_to_api():
    """Verify component defaults to API."""
    settings = AppSettings()
    assert settings.component == Component.API


def test_component_from_env(monkeypatch):
    """Verify GLAC_COMPONENT env var sets the component."""
    monkeypatch.setenv("GLAC_COMPONENT", "scheduler")
    settings = AppSettings()
    assert settings.component == Component.SCHEDULER


def test_scheduler_settings_nested(monkeypatch):
    """Verify GLAC_SCHEDULER__INTERVAL_SECONDS sets scheduler interval."""
    monkeypatch.setenv("GLAC_SCHEDULER__INTERVAL_SECONDS", "60")
    settings = AppSettings()
    assert settings.scheduler.interval_seconds == 60


def test_messaging_settings_nested(monkeypatch):
    """Verify GLAC_MESSAGING__INTERVAL_SECONDS sets messaging interval."""
    monkeypatch.setenv("GLAC_MESSAGING__INTERVAL_SECONDS", "10")
    settings = AppSettings()
    assert settings.messaging.interval_seconds == 10
