"""Test E2eSettings, which the e2e reads from the pod's environment."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from e2e.support import E2eSettings

if TYPE_CHECKING:
    from pathlib import Path


def _environment(credential_file: Path) -> dict[str, str]:
    return {
        "E2E_API_URL": "http://api:8000",
        "GLAC_CATALOG__URI": "http://polaris:8181/api/catalog",
        "GLAC_CATALOG__MANAGEMENT_URI": "http://polaris:8181/api/management/v1",
        "GLAC_CATALOG__SCOPE": "PRINCIPAL_ROLE:ALL",
        "E2E_CATALOG": "iceberg",
        "E2E_POLARIS_CREDENTIAL_FILE": str(credential_file),
        "GLAC_CATALOG__S3_ENDPOINT": "http://rustfs:9000",
        "GLAC_CATALOG__S3_REGION": "dummy-region",
        "AWS_ACCESS_KEY_ID": "access-key-value",
        "AWS_SECRET_ACCESS_KEY": "secret-key-value",
        "GLAC_TEMPORAL__ADDRESS": "temporal:7233",
        "GLAC_TEMPORAL__NAMESPACE": "default",
    }


def test_reads_every_setting_and_the_credential_file(tmp_path):
    """Each setting comes from its variable, and the Polaris credential from the file the pod mounts."""
    credential = tmp_path / "polaris"
    credential.write_text("client-id:client-secret-value\n")
    settings = E2eSettings.from_environment(_environment(credential))
    assert settings.api_url == "http://api:8000"
    assert settings.catalog_uri == "http://polaris:8181/api/catalog"
    assert settings.management_uri == "http://polaris:8181/api/management/v1"
    assert settings.scope == "PRINCIPAL_ROLE:ALL"
    assert settings.catalog == "iceberg"
    assert settings.polaris_credential == "client-id:client-secret-value"
    assert settings.s3_endpoint == "http://rustfs:9000"
    assert settings.s3_region == "dummy-region"
    assert settings.s3_access_key_id == "access-key-value"
    assert settings.s3_secret_access_key == "secret-key-value"
    assert settings.temporal_address == "temporal:7233"
    assert settings.temporal_namespace == "default"


def test_a_missing_variable_is_named(tmp_path):
    """A pod started without a variable fails saying which one."""
    credential = tmp_path / "polaris"
    credential.write_text("id:secret")
    environment = _environment(credential)
    del environment["GLAC_TEMPORAL__ADDRESS"]
    with pytest.raises(KeyError, match="GLAC_TEMPORAL__ADDRESS"):
        E2eSettings.from_environment(environment)


def test_repr_hides_the_secrets(tmp_path):
    """Printing the settings in a failure report shows no credential."""
    credential = tmp_path / "polaris"
    credential.write_text("client-id:client-secret-value")
    text = repr(E2eSettings.from_environment(_environment(credential)))
    for secret in ("client-secret-value", "access-key-value", "secret-key-value"):
        assert secret not in text
