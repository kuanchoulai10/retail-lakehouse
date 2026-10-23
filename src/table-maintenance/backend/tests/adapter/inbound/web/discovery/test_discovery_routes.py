"""Test the discovery routes."""

from __future__ import annotations

from application.port.inbound.discovery.get_discovery_settings import (
    GetDiscoverySettingsUseCaseOutput,
)
from application.port.inbound.discovery.sync_discovered_tables import (
    SyncDiscoveredTablesUseCaseInput,
    SyncDiscoveredTablesUseCaseOutput,
)
from application.port.inbound.discovery.update_discovery_settings import (
    UpdateDiscoverySettingsUseCaseInput,
    UpdateDiscoverySettingsUseCaseOutput,
)
from tests.adapter.inbound.web.web_test_support import NOW, StubUseCase, build_client


def test_get_discovery_settings() -> None:
    stub = StubUseCase(GetDiscoverySettingsUseCaseOutput(enabled=True, updated_at=NOW))
    client = build_client(get_discovery_settings=stub)

    response = client.get("/v1/discovery")

    assert response.status_code == 200
    assert response.json()["enabled"] is True


def test_put_discovery_settings() -> None:
    stub = StubUseCase(
        UpdateDiscoverySettingsUseCaseOutput(enabled=False, updated_at=NOW)
    )
    client = build_client(update_discovery_settings=stub)

    response = client.put("/v1/discovery", json={"enabled": False})

    assert response.status_code == 200
    assert response.json()["enabled"] is False
    assert stub.requests == [UpdateDiscoverySettingsUseCaseInput(enabled=False)]


def test_put_discovery_settings_rejects_unknown_key() -> None:
    response = build_client().put("/v1/discovery", json={"enabled": True, "x": 1})

    assert response.status_code == 422


def test_scan_returns_202_with_counts() -> None:
    stub = StubUseCase(
        SyncDiscoveredTablesUseCaseOutput(registered=2, renamed=0, dropped=1, skipped=3)
    )
    client = build_client(sync_discovered_tables=stub)

    response = client.post(
        "/v1/discovery/scan", json={"catalog": "iceberg", "namespace": "sales"}
    )

    assert response.status_code == 202
    assert response.json() == {
        "registered": 2,
        "renamed": 0,
        "dropped": 1,
        "skipped": 3,
    }
    assert stub.requests == [
        SyncDiscoveredTablesUseCaseInput(catalog="iceberg", namespace="sales")
    ]


def test_scan_namespace_is_optional() -> None:
    stub = StubUseCase(
        SyncDiscoveredTablesUseCaseOutput(registered=0, renamed=0, dropped=0, skipped=0)
    )
    client = build_client(sync_discovered_tables=stub)

    response = client.post("/v1/discovery/scan", json={"catalog": "iceberg"})

    assert response.status_code == 202
    assert stub.requests == [SyncDiscoveredTablesUseCaseInput(catalog="iceberg")]
