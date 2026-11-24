"""Test sweep_leftovers, which removes what an earlier run that was cut short left on the platform."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import cast

import httpx
from pyarrow import fs
from pyiceberg.catalog import Catalog
from temporalio.client import Client, WorkflowExecutionStatus

from e2e.support import KubernetesApi, PlatformApi, PolarisClient, TemporalSession, sweep_leftovers

NS = "e2e_1a2b3c4d_orders"
DISCOVERY = "tm-e2e-1a2b3c4d-orders"
MAINTENANCE = "tm-e2e-orders-1a2b3c4d"
CATALOG = "tm_e2e_catalog_1a2b3c4d_round_trip"
ORPHAN = "tm_e2e_catalog_9f9f9f9f_lifecycle"
MANAGEMENT = "/api/management/v1"


class _Iceberg:
    def __init__(self, events: list[str], namespaces: list[str]) -> None:
        self._events = events
        self._namespaces = namespaces

    def list_namespaces(self) -> list[tuple[str, ...]]:
        return [(namespace,) for namespace in self._namespaces]

    def list_tables(self, namespace: str) -> list[tuple[str, str]]:
        return [(namespace, "tm_e2e_orders")] if namespace == NS else []

    def load_namespace_properties(self, namespace: str) -> dict[str, str]:
        return {"location": f"s3://lake/warehouse/{namespace}/"}

    def load_table(self, identifier: tuple[str, str]) -> SimpleNamespace:
        return SimpleNamespace(location=lambda: f"s3://lake/warehouse/{identifier[0]}/{identifier[1]}")

    def drop_table(self, identifier: tuple[str, str]) -> None:
        self._events.append(f"drop table {'.'.join(identifier)}")

    def drop_namespace(self, namespace: str) -> None:
        self._events.append(f"drop namespace {namespace}")


class _Temporal:
    def __init__(self, events: list[str]) -> None:
        self._events = events

    def get_workflow_handle(self, workflow_id: str) -> SimpleNamespace:
        async def describe() -> SimpleNamespace:
            self._events.append(f"describe {workflow_id}")
            return SimpleNamespace(status=WorkflowExecutionStatus.COMPLETED)

        return SimpleNamespace(describe=describe)


def _platform(events: list[str], *, leftovers: bool) -> PlatformApi:
    answers = {
        "/v1/discovery-policies": {"policies": [{"name": "default"}, *([{"name": DISCOVERY}] if leftovers else [])]},
        f"/v1/discovery-policies/{DISCOVERY}/attachments": {"attachments": [{"id": "da-1"}]},
        "/v1/discovery-policies/default/attachments": {
            "attachments": [
                *(
                    [{"id": "da-d1", "target": {"type": "table", "path": [CATALOG, "lifecycle", "t1"]}}]
                    if leftovers
                    else []
                ),
                {"id": "da-d2", "target": {"type": "catalog", "path": ["iceberg"]}},
            ]
        },
        "/v1/maintenance-policies/default/attachments": {
            "attachments": [
                *([{"id": "pa-d1", "target": {"type": "namespace", "path": [CATALOG, "ns"]}}] if leftovers else []),
                {"id": "pa-d2", "target": {"type": "namespace", "path": ["iceberg", "inventory"]}},
            ]
        },
        "/v1/maintenance-policies": {
            "policies": [{"name": "default"}, *([{"name": MAINTENANCE}] if leftovers else [])]
        },
        f"/v1/maintenance-policies/{MAINTENANCE}/attachments": {"attachments": [{"id": "pa-1"}]},
        "/v1/tables": [
            {"catalog": "iceberg", "namespace": NS, "table": "tm_e2e_orders", "status": "unmanaged", "uuid": "u1"},
            {"catalog": CATALOG, "namespace": "lifecycle", "table": "t", "status": "unmanaged", "uuid": "u2"},
            {"catalog": "iceberg", "namespace": "inventory", "table": "orders", "status": "managed", "uuid": "u3"},
        ],
        "/v1/catalogs": [{"name": "iceberg"}, *([{"name": CATALOG}] if leftovers else [])],
    }

    def handle(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, json=answers[request.url.path])
        events.append(f"{request.method} {request.url.path}")
        return httpx.Response(204)

    return PlatformApi(httpx.Client(transport=httpx.MockTransport(handle), base_url="http://api"))


def _polaris(events: list[str]) -> PolarisClient:
    def handle(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/oauth/tokens"):
            return httpx.Response(200, json={"access_token": "token"})
        if request.method == "GET":
            return httpx.Response(200, json={"roles": []} if path.endswith("catalog-roles") else {})
        events.append(f"polaris {request.method} {path.removeprefix(MANAGEMENT)}")
        return httpx.Response(204)

    return PolarisClient(
        httpx.Client(transport=httpx.MockTransport(handle)),
        catalog_uri="http://polaris/api/catalog",
        management_uri="http://polaris" + MANAGEMENT,
        credential="e2e-id:e2e-secret",
        scope="PRINCIPAL_ROLE:ALL",
    )


HOLDER = "tm-e2e-holder-9f9f9f9f-maintenance-queue"
PODGROUPS = "/apis/scheduling.volcano.sh/v1beta1/namespaces/lakehouse-maintenance-operations/podgroups"


def _kubernetes(events: list[str], *, leftovers: bool) -> KubernetesApi:
    def handle(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            assert request.url.params["labelSelector"] == (
                "app.kubernetes.io/name=table-maintenance-e2e,app.kubernetes.io/component=queue-holder"
            )
            names = [HOLDER, "someone-elses"] if leftovers else []
            return httpx.Response(200, json={"items": [{"metadata": {"name": name}} for name in names]})
        events.append(f"{request.method} {request.url.path}")
        return httpx.Response(200, json={})

    return KubernetesApi(httpx.Client(transport=httpx.MockTransport(handle), base_url="https://kubernetes"))


def _storage(tmp_path, *paths: str) -> fs.SubTreeFileSystem:
    for path in paths:
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / path).write_text("x")
    return fs.SubTreeFileSystem(str(tmp_path), fs.LocalFileSystem())


def _sweep(tmp_path, events: list[str], *, leftovers: bool, namespaces: list[str], storage: list[str]) -> list[str]:
    temporal = TemporalSession(asyncio.new_event_loop(), cast(Client, _Temporal(events)))
    try:
        return sweep_leftovers(
            platform=_platform(events, leftovers=leftovers),
            iceberg=cast(Catalog, _Iceberg(events, namespaces)),
            s3=_storage(tmp_path, *storage),
            polaris=_polaris(events),
            temporal=temporal,
            kubernetes=_kubernetes(events, leftovers=leftovers),
            catalog="iceberg",
        )
    finally:
        temporal.close()


def test_what_a_cut_short_run_left_is_removed_in_the_order_its_cleanup_would_have(tmp_path):
    """Discovery goes first and the table is unmanaged before its maintenance policy and the table go."""
    events: list[str] = []
    removed = _sweep(
        tmp_path,
        events,
        leftovers=True,
        namespaces=["inventory", NS],
        storage=[
            f"lake/warehouse/{NS}/tm_e2e_orders/data/f.parquet",
            "lake/warehouse/inventory/items/data/f.parquet",
            f"tm-e2e-catalogs/{CATALOG}/ns/t/metadata.json",
            f"tm-e2e-catalogs/{ORPHAN}/ns/t/metadata.json",
        ],
    )
    assert events == [
        f"DELETE {PODGROUPS}/{HOLDER}",
        f"DELETE /v1/discovery-policies/{DISCOVERY}/attachments/da-1",
        f"DELETE /v1/discovery-policies/{DISCOVERY}",
        "DELETE /v1/discovery-policies/default/attachments/da-d1",
        "describe table-reconciliation:table-uuid=u1",
        "describe table-reconciliation:table-uuid=u2",
        f"DELETE /v1/maintenance-policies/{MAINTENANCE}/attachments/pa-1",
        f"DELETE /v1/maintenance-policies/{MAINTENANCE}",
        "DELETE /v1/maintenance-policies/default/attachments/pa-d1",
        f"drop table {NS}.tm_e2e_orders",
        f"drop namespace {NS}",
        f"polaris PUT /catalogs/{CATALOG}/catalog-roles/catalog_admin/grants",
        f"polaris PUT /catalogs/{CATALOG}/catalog-roles/catalog_admin/grants",
        f"polaris DELETE /catalogs/{CATALOG}",
    ]
    assert removed == [
        f"queue holder {HOLDER}",
        f"discovery policy {DISCOVERY}",
        f"default discovery policy's attachment da-d1 on {CATALOG}.lifecycle.t1",
        f"maintenance policy {MAINTENANCE}",
        f"default maintenance policy's attachment pa-d1 on {CATALOG}.ns",
        f"namespace {NS}",
        f"catalog {CATALOG}",
        f"storage s3://tm-e2e-catalogs/{ORPHAN}/",
    ]
    assert not (tmp_path / "lake/warehouse" / NS).exists()
    assert (tmp_path / "lake/warehouse/inventory/items/data/f.parquet").exists()
    assert sorted(p.name for p in (tmp_path / "tm-e2e-catalogs").iterdir()) == []


def test_a_platform_with_nothing_left_is_left_alone(tmp_path):
    """The platform's own policies, namespaces and catalog are never touched."""
    events: list[str] = []
    removed = _sweep(
        tmp_path,
        events,
        leftovers=False,
        namespaces=["inventory"],
        storage=["lake/warehouse/inventory/items/data/f.parquet"],
    )
    assert (events, removed) == ([], [])
    assert (tmp_path / "lake/warehouse/inventory/items/data/f.parquet").exists()
