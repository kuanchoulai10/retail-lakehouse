"""Test settings validation through the real table maintenance preset service."""

from __future__ import annotations

import pytest

from context.table_maintenance.application.service.table_maintenance_preset import (
    CreateTableMaintenancePresetService,
)
from tests.context.table_maintenance.adapter.inbound.web.web_test_support import (
    build_client,
)
from tests.context.table_maintenance.fakes.in_memory_table_maintenance_presets_repo import (
    InMemoryTableMaintenancePresetsRepo,
)


@pytest.fixture
def client():
    """Provide a test client wired to a create preset service."""
    service = CreateTableMaintenancePresetService(InMemoryTableMaintenancePresetsRepo())
    return build_client(create_table_maintenance_preset=service)


def test_orphan_older_than_below_one_day_returns_422(client) -> None:
    """An orphan file retention below one day is rejected with 422 and a detail."""
    response = client.post(
        "/v1/table-maintenance-presets",
        json={
            "name": "risky",
            "settings": {"remove_orphan_files": {"older_than_seconds": 3600}},
        },
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "remove_orphan_files.older_than_seconds: must be at least 1 day"}


def test_unknown_settings_key_returns_422(client) -> None:
    """An unknown settings key is rejected with 422."""
    response = client.post(
        "/v1/table-maintenance-presets",
        json={"name": "typo", "settings": {"expire_snapshot": {"enabled": True}}},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "expire_snapshot: Extra inputs are not permitted"}


def test_valid_settings_are_created(client) -> None:
    """Valid settings are accepted with 201 and kept in seconds."""
    response = client.post(
        "/v1/table-maintenance-presets",
        json={
            "name": "ok",
            "settings": {"remove_orphan_files": {"older_than_seconds": 172800}},
        },
    )

    assert response.status_code == 201
    orphan = response.json()["settings"]["remove_orphan_files"]
    assert orphan["older_than_seconds"] == 172800


def test_nested_domain_field_name_returns_422(client) -> None:
    """A nested field name is not a wire name: ``older_than`` is rejected, only ``older_than_seconds`` is read."""
    response = client.post(
        "/v1/table-maintenance-presets",
        json={"name": "named", "settings": {"remove_orphan_files": {"older_than": 172800}}},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "remove_orphan_files.older_than: Extra inputs are not permitted"}
