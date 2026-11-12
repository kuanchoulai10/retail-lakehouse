"""Test the object-store file system that reads the Spark event logs."""

from __future__ import annotations

from pydantic import SecretStr

from bootstrap.configs import AppSettings, CatalogSettings, SparkSettings
from bootstrap.container import build_event_log_filesystem, event_log_base


def _options(settings: AppSettings) -> dict:
    return build_event_log_filesystem(settings).__reduce__()[1][0]


def test_filesystem_uses_the_catalog_endpoint_and_region():
    """The file system talks to the catalog's object store, path style, in its region."""
    options = _options(
        AppSettings(catalog=CatalogSettings(s3_endpoint="http://rustfs.object-storage:9000", s3_region="eu-1"))
    )
    assert options["endpoint_override"] == "rustfs.object-storage:9000"
    assert options["scheme"] == "http"
    assert options["region"] == "eu-1"
    assert options["force_virtual_addressing"] is False


def test_filesystem_follows_an_https_endpoint():
    """An https endpoint gives the https scheme."""
    assert _options(AppSettings(catalog=CatalogSettings(s3_endpoint="https://s3.example.com")))["scheme"] == "https"


def test_filesystem_uses_the_catalog_keys_when_set():
    """The catalog's S3 keys are used when they are configured."""
    options = _options(
        AppSettings(catalog=CatalogSettings(s3_access_key_id=SecretStr("AKID"), s3_secret_access_key=SecretStr("SK")))
    )
    assert (options["access_key"], options["secret_key"]) == ("AKID", "SK")


def test_filesystem_without_keys_leaves_credentials_to_the_environment():
    """Without catalog keys no key is set, so the AWS environment chain supplies them."""
    options = _options(AppSettings())
    assert (options["access_key"], options["secret_key"]) == (None, None)


def test_event_log_base_drops_scheme_and_slash():
    """The event log directory is read as a bucket path without its s3a scheme and trailing slash."""
    assert event_log_base(AppSettings()) == "spark-event-logs"
    assert event_log_base(AppSettings(spark=SparkSettings(event_log_dir="s3a://logs/spark/"))) == "logs/spark"
