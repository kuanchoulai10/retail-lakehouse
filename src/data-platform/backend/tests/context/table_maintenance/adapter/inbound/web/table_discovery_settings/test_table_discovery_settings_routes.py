"""Test the discovery routes."""

from __future__ import annotations

from context.table_maintenance.application.port.inbound.table import (
    SyncDiscoveredTablesUseCaseInput,
    SyncDiscoveredTablesUseCaseOutput,
)
from context.table_maintenance.application.port.inbound.table_discovery_settings import (
    GetTableDiscoverySettingsUseCaseOutput,
    ListCoveredCatalogsUseCaseInput,
    ListCoveredCatalogsUseCaseOutput,
    UpdateTableDiscoverySettingsUseCaseInput,
    UpdateTableDiscoverySettingsUseCaseOutput,
)
from tests.context.table_maintenance.adapter.inbound.web.web_test_support import (
    NOW,
    StubUseCase,
    build_client,
)


def test_get_table_discovery_settings() -> None:
    """Getting the settings returns whether discovery is enabled."""
    stub = StubUseCase(GetTableDiscoverySettingsUseCaseOutput(enabled=True, updated_at=NOW))
    client = build_client(get_table_discovery_settings=stub)

    response = client.get("/v1/table-discovery-settings")

    assert response.status_code == 200
    assert response.json()["enabled"] is True


def test_put_table_discovery_settings() -> None:
    """Putting the settings returns the new value and passes it to the use case."""
    stub = StubUseCase(UpdateTableDiscoverySettingsUseCaseOutput(enabled=False, updated_at=NOW))
    client = build_client(update_table_discovery_settings=stub)

    response = client.put("/v1/table-discovery-settings", json={"enabled": False})

    assert response.status_code == 200
    assert response.json()["enabled"] is False
    assert stub.requests == [UpdateTableDiscoverySettingsUseCaseInput(enabled=False)]


def test_put_table_discovery_settings_rejects_unknown_key() -> None:
    """Putting settings with an unknown key is rejected with 422."""
    response = build_client().put("/v1/table-discovery-settings", json={"enabled": True, "x": 1})

    assert response.status_code == 422


def test_scan_returns_202_with_counts() -> None:
    """A scan returns 202 with the sync counts and passes the catalog and namespace on."""
    stub = StubUseCase(SyncDiscoveredTablesUseCaseOutput(registered=2, renamed=0, dropped=1, skipped=3))
    client = build_client(sync_discovered_tables=stub)

    response = client.post(
        "/v1/table-discovery-settings/scan",
        json={"catalog": "iceberg", "namespace": "sales"},
    )

    assert response.status_code == 202
    assert response.json() == {
        "registered": 2,
        "renamed": 0,
        "dropped": 1,
        "skipped": 3,
        "ensured": 0,
    }
    assert stub.requests == [SyncDiscoveredTablesUseCaseInput(catalog="iceberg", namespace="sales")]


def test_scan_namespace_is_optional() -> None:
    """A scan without a namespace passes only the catalog."""
    stub = StubUseCase(SyncDiscoveredTablesUseCaseOutput(registered=0, renamed=0, dropped=0, skipped=0))
    client = build_client(sync_discovered_tables=stub)

    response = client.post("/v1/table-discovery-settings/scan", json={"catalog": "iceberg"})

    assert response.status_code == 202
    assert stub.requests == [SyncDiscoveredTablesUseCaseInput(catalog="iceberg")]


def test_old_discovery_prefix_is_gone() -> None:
    """The old discovery prefix returns 404 for its routes."""
    client = build_client()

    assert client.get("/v1/discovery").status_code == 404
    assert client.post("/v1/discovery/scan", json={}).status_code == 404


def test_covered_catalogs_route() -> None:
    """Listing the covered catalogs returns the names the use case reports."""
    stub = StubUseCase(ListCoveredCatalogsUseCaseOutput(catalogs=["iceberg", "other"]))
    client = build_client(list_covered_catalogs=stub)

    response = client.get("/v1/table-discovery-settings/catalogs")

    assert response.status_code == 200
    assert response.json() == {"catalogs": ["iceberg", "other"]}
    assert stub.requests == [ListCoveredCatalogsUseCaseInput()]
