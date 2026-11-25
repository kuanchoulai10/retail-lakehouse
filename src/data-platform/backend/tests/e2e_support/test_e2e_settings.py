"""Test E2eSettings, which the e2e reads from the pod's environment and the worker's settings file."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from e2e.support import E2eSettings

if TYPE_CHECKING:
    from pathlib import Path


def _environment(
    tmp_path: Path, worker_config: str = "maintenance:\n  compaction_quiet_seconds: 60\n"
) -> dict[str, str]:
    credential = tmp_path / "polaris"
    credential.write_text("client-id:client-secret-value\n")
    config = tmp_path / "config.yaml"
    config.write_text(worker_config)
    return {
        "E2E_API_URL": "http://api:8000",
        "E2E_CATALOG_URI": "http://polaris:8181/api/catalog",
        "E2E_MANAGEMENT_URI": "http://polaris:8181/api/management/v1",
        "E2E_CATALOG_SCOPE": "PRINCIPAL_ROLE:ALL",
        "E2E_CATALOG": "iceberg",
        "E2E_POLARIS_CREDENTIAL_FILE": str(credential),
        "E2E_S3_ENDPOINT": "http://rustfs:9000",
        "AWS_REGION": "dummy-region",
        "AWS_ACCESS_KEY_ID": "access-key-value",
        "AWS_SECRET_ACCESS_KEY": "secret-key-value",
        "E2E_TEMPORAL_ADDRESS": "temporal:7233",
        "E2E_TEMPORAL_NAMESPACE": "default",
        "E2E_WORKER_CONFIG_FILE": str(config),
    }


def test_reads_every_setting_and_the_credential_file(tmp_path):
    """Each setting comes from its variable, and the Polaris credential from the file the pod mounts."""
    settings = E2eSettings.from_environment(_environment(tmp_path))
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


def test_reads_the_maintenance_settings_the_worker_was_given(tmp_path):
    """The worker's settings file is read as written, so a scenario compares the page with what the worker got."""
    settings = E2eSettings.from_environment(_environment(tmp_path))
    assert settings.worker_maintenance == {"compaction_quiet_seconds": 60}


def test_a_worker_given_no_maintenance_settings_reads_as_empty(tmp_path):
    """A settings file with no maintenance block means the worker runs every default."""
    settings = E2eSettings.from_environment(_environment(tmp_path, "database:\n  backend: postgres\n"))
    assert settings.worker_maintenance == {}


def test_takes_no_glac_variable(tmp_path):
    """The e2e is not a glac role: none of its settings come from a GLAC_ variable."""
    environment = _environment(tmp_path)
    assert not [name for name in environment if name.startswith("GLAC_")]
    E2eSettings.from_environment(environment)


def test_a_missing_variable_is_named(tmp_path):
    """A pod started without a variable fails saying which one."""
    environment = _environment(tmp_path)
    del environment["E2E_TEMPORAL_ADDRESS"]
    with pytest.raises(KeyError, match="E2E_TEMPORAL_ADDRESS"):
        E2eSettings.from_environment(environment)


def test_repr_hides_the_secrets(tmp_path):
    """Printing the settings in a failure report shows no credential."""
    text = repr(E2eSettings.from_environment(_environment(tmp_path)))
    for secret in ("client-secret-value", "access-key-value", "secret-key-value"):
        assert secret not in text
