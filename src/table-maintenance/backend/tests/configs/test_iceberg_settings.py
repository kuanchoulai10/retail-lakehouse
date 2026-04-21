"""Tests for AppSettings Iceberg catalog configuration."""

from configs import AppSettings


def test_iceberg_catalog_uri_default():
    """Verify that iceberg_catalog_uri defaults to Polaris endpoint."""
    s = AppSettings()
    assert s.iceberg_catalog_uri == "http://polaris:8181/api/catalog"


def test_iceberg_catalog_name_default():
    """Verify that iceberg_catalog_name defaults to 'iceberg'."""
    s = AppSettings()
    assert s.iceberg_catalog_name == "iceberg"


def test_iceberg_catalog_uri_env_override(monkeypatch):
    """Verify that BACKEND_ICEBERG_CATALOG_URI overrides the default."""
    monkeypatch.setenv("BACKEND_ICEBERG_CATALOG_URI", "http://custom:9999/api/catalog")
    s = AppSettings()
    assert s.iceberg_catalog_uri == "http://custom:9999/api/catalog"


def test_iceberg_catalog_name_env_override(monkeypatch):
    """Verify that BACKEND_ICEBERG_CATALOG_NAME overrides the default."""
    monkeypatch.setenv("BACKEND_ICEBERG_CATALOG_NAME", "my_catalog")
    s = AppSettings()
    assert s.iceberg_catalog_name == "my_catalog"
