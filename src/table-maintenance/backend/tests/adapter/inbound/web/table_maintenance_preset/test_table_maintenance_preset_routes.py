"""Test the table maintenance preset routes."""

from __future__ import annotations

from typing import Any

from application.port.inbound.table_maintenance_preset.create_table_maintenance_preset import (
    CreateTableMaintenancePresetUseCaseInput,
    CreateTableMaintenancePresetUseCaseOutput,
)
from application.port.inbound.table_maintenance_preset.delete_table_maintenance_preset import (
    DeleteTableMaintenancePresetUseCaseInput,
    DeleteTableMaintenancePresetUseCaseOutput,
)
from application.port.inbound.table_maintenance_preset.get_table_maintenance_preset import (
    GetTableMaintenancePresetUseCaseInput,
    GetTableMaintenancePresetUseCaseOutput,
)
from application.port.inbound.table_maintenance_preset.list_table_maintenance_presets import (
    ListTableMaintenancePresetsUseCaseOutput,
    ListTableMaintenancePresetsUseCaseOutputItem,
)
from application.port.inbound.table_maintenance_preset.update_table_maintenance_preset import (
    UpdateTableMaintenancePresetUseCaseInput,
    UpdateTableMaintenancePresetUseCaseOutput,
)
from tests.adapter.inbound.web.web_test_support import NOW, StubUseCase, build_client

FIELDS: dict[str, Any] = {
    "id": "t-1",
    "name": "gold",
    "settings": {"reconcile_interval_seconds": 3600},
    "created_at": NOW,
    "updated_at": NOW,
}


def test_list_table_maintenance_presets() -> None:
    output = ListTableMaintenancePresetsUseCaseOutput(
        items=[ListTableMaintenancePresetsUseCaseOutputItem(**FIELDS)]
    )
    client = build_client(list_table_maintenance_presets=StubUseCase(output))

    response = client.get("/v1/table-maintenance-presets")

    assert response.status_code == 200
    assert response.json()[0]["name"] == "gold"


def test_create_table_maintenance_preset_returns_201() -> None:
    stub = StubUseCase(CreateTableMaintenancePresetUseCaseOutput(**FIELDS))
    client = build_client(create_table_maintenance_preset=stub)

    response = client.post(
        "/v1/table-maintenance-presets",
        json={"name": "gold", "settings": {"reconcile_interval_seconds": 3600}},
    )

    assert response.status_code == 201
    assert response.json()["settings"] == {"reconcile_interval_seconds": 3600}
    assert stub.requests == [
        CreateTableMaintenancePresetUseCaseInput(
            name="gold", settings={"reconcile_interval_seconds": 3600}
        )
    ]


def test_get_table_maintenance_preset() -> None:
    stub = StubUseCase(GetTableMaintenancePresetUseCaseOutput(**FIELDS))
    client = build_client(get_table_maintenance_preset=stub)

    response = client.get("/v1/table-maintenance-presets/t-1")

    assert response.status_code == 200
    assert stub.requests == [GetTableMaintenancePresetUseCaseInput(id="t-1")]


def test_update_table_maintenance_preset_keeps_omitted_fields_unset() -> None:
    stub = StubUseCase(UpdateTableMaintenancePresetUseCaseOutput(**FIELDS))
    client = build_client(update_table_maintenance_preset=stub)

    response = client.patch(
        "/v1/table-maintenance-presets/t-1", json={"name": "platinum"}
    )

    assert response.status_code == 200
    assert stub.requests == [
        UpdateTableMaintenancePresetUseCaseInput(
            id="t-1", name="platinum", settings=None
        )
    ]


def test_delete_table_maintenance_preset_returns_204() -> None:
    stub = StubUseCase(DeleteTableMaintenancePresetUseCaseOutput())
    client = build_client(delete_table_maintenance_preset=stub)

    response = client.delete("/v1/table-maintenance-presets/t-1")

    assert response.status_code == 204
    assert stub.requests == [DeleteTableMaintenancePresetUseCaseInput(id="t-1")]


def test_old_prefix_is_gone() -> None:
    client = build_client()

    assert client.get("/v1/" + "-".join(["policy", "templates"])).status_code == 404
