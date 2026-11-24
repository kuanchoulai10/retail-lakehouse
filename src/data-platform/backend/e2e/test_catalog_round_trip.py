"""A catalog, its namespaces, a table, a generic table and a view round-trip through the API to Polaris.

Each write goes through the table maintenance API and is read back from Polaris as the e2e principal,
which holds ``service_admin`` and so the new catalog's ``catalog_admin``. Each delete is followed by
Polaris's 404. Whatever a failed run leaves behind is dropped by the cleanup, with its storage prefix.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib.parse import quote

import pytest
from pyarrow import fs

from e2e.support import drop_catalog

if TYPE_CHECKING:
    import httpx

    from e2e.support import CleanupStack, E2eSettings, PolarisClient

pytestmark = pytest.mark.critical

BUCKET = "tm-e2e-catalogs"
RELOAD = "changed since you loaded it, reload"


def _ns(*parts: str) -> str:
    return quote("\x1f".join(parts), safe="")


def _ok(reply: httpx.Response) -> Any:  # noqa: ANN401
    assert reply.is_success, f"{reply.request.method} {reply.request.url} answered {reply.status_code}: {reply.text}"
    return reply.json() if reply.content else None


def _gone(reply: httpx.Response, what: str) -> None:
    assert reply.status_code == 404, f"{what} still exists in Polaris after the delete: {reply.text}"


def _names(reply: httpx.Response) -> list[str]:
    return [entry["name"] for entry in _ok(reply)]


def _namespaces(reply: httpx.Response) -> list[list[str]]:
    return [entry["namespace"] for entry in _ok(reply)]


def _remove_prefix(s3: fs.S3FileSystem, prefix: str) -> None:
    """Remove the prefix with its directory marker (``delete_dir_contents`` would keep the marker)."""
    if s3.get_file_info(prefix).type != fs.FileType.NotFound:
        s3.delete_dir(prefix)


def test_a_catalog_round_trips_through_the_api_to_polaris(
    api: httpx.Client,
    polaris: PolarisClient,
    s3: fs.S3FileSystem,
    settings: E2eSettings,
    suffix: str,
    cleanup: CleanupStack,
):
    """Every write the API accepts is in Polaris as written, and every delete leaves nothing behind."""
    catalog = f"tm_e2e_catalog_{suffix}"
    base = f"s3://{BUCKET}/{catalog}"
    prefix = f"{BUCKET}/{catalog}"
    if s3.get_file_info(BUCKET).type == fs.FileType.NotFound:
        s3.create_dir(BUCKET)
    cleanup.push(f"remove s3://{prefix}/", lambda: _remove_prefix(s3, prefix))
    cleanup.push(f"drop catalog {catalog}", lambda: drop_catalog(polaris, catalog))

    _catalog(api, polaris, settings, catalog, base)
    _namespaces_of(api, polaris, catalog)
    _table(api, polaris, catalog, base)
    _generic_table_and_view(api, polaris, catalog, base)
    _deletes(api, polaris, catalog)

    _remove_prefix(s3, prefix)
    assert s3.get_file_info(prefix).type == fs.FileType.NotFound, f"s3://{prefix}/ is still there"


def _catalog(api: httpx.Client, polaris: PolarisClient, settings: E2eSettings, catalog: str, base: str) -> None:
    platform = _ok(api.get(f"/v1/catalogs/{settings.catalog}"))["storage_config"]
    storage = {
        "storage_type": platform["storage_type"],
        "allowed_locations": [base],
        "endpoint": platform["endpoint"],
        "sts_endpoint": platform["sts_endpoint"],
        "path_style_access": platform["path_style_access"],
    }
    created = _ok(
        api.post(
            "/v1/catalogs",
            json={"name": catalog, "type": "INTERNAL", "default_base_location": base, "storage_config": storage},
        )
    )
    held = _ok(polaris.management("GET", f"/catalogs/{catalog}"))
    assert held["type"] == "INTERNAL"
    assert held["properties"]["default-base-location"] == base
    assert base in [location.rstrip("/") for location in held["storageConfigInfo"]["allowedLocations"]]
    grants = _ok(polaris.management("GET", f"/catalogs/{catalog}/catalog-roles/catalog_admin/grants"))["grants"]
    assert {"type": "catalog", "privilege": "CATALOG_MANAGE_CONTENT"} in [
        {"type": grant["type"], "privilege": grant["privilege"]} for grant in grants
    ]
    assert catalog in _names(api.get("/v1/catalogs"))

    version = created["entity_version"]
    update = {"entity_version": version, "default_base_location": base, "storage_config": storage}
    _ok(api.put(f"/v1/catalogs/{catalog}", json={**update, "properties": {"tm-e2e": "updated"}}))
    assert _ok(polaris.management("GET", f"/catalogs/{catalog}"))["properties"]["tm-e2e"] == "updated"
    ours = api.put(f"/v1/catalogs/{catalog}", json={**update, "properties": {"tm-e2e": "stale"}})
    theirs = polaris.management(
        "PUT", f"/catalogs/{catalog}", json={"currentEntityVersion": version, "properties": {"tm-e2e": "stale"}}
    )
    assert theirs.status_code == 409, theirs.text
    assert theirs.json()["error"]["message"]
    assert ours.status_code == 409, ours.text
    assert ours.json()["detail"].endswith(RELOAD)


def _namespaces_of(api: httpx.Client, polaris: PolarisClient, catalog: str) -> None:
    namespaces = f"/v1/catalogs/{catalog}/namespaces"
    _ok(api.post(namespaces, json={"namespace": ["tm_e2e"], "properties": {"owner": "tm-e2e"}}))
    _ok(api.post(namespaces, json={"namespace": ["tm_e2e", "a.b"]}))
    assert _ok(polaris.catalog("GET", f"/v1/{catalog}/namespaces/{_ns('tm_e2e', 'a.b')}"))["namespace"] == [
        "tm_e2e",
        "a.b",
    ]
    assert ["tm_e2e"] in _namespaces(api.get(namespaces))
    assert ["tm_e2e", "a.b"] in _namespaces(api.get(namespaces, params={"parent": "tm_e2e"}))
    _ok(api.put(f"{namespaces}/tm_e2e/properties", json={"updates": {"stage": "round-trip"}, "removals": ["owner"]}))
    properties = _ok(polaris.catalog("GET", f"/v1/{catalog}/namespaces/tm_e2e"))["properties"]
    assert properties["stage"] == "round-trip"
    assert "owner" not in properties


def _table(api: httpx.Client, polaris: PolarisClient, catalog: str, base: str) -> None:
    child = _ns("tm_e2e", "a.b")
    tables = f"/v1/catalogs/{catalog}/namespaces/{child}/tables"
    held_at = f"/v1/{catalog}/namespaces/{child}/tables"
    location = f"{base}/tm_e2e/a.b/rt_orders_custom"
    created = _ok(
        api.post(
            tables,
            json={
                "name": "rt_orders",
                "schema_fields": [
                    {"name": "id", "type": "long"},
                    {"name": "order_ts", "type": "timestamptz", "required": False},
                ],
                "partition_fields": [{"source_column": "order_ts", "transform": "day"}],
                "location": location,
                "properties": {"tm-e2e": "created"},
            },
        )
    )
    uuid = created["uuid"]
    metadata = _ok(polaris.catalog("GET", f"{held_at}/rt_orders"))["metadata"]
    assert metadata["table-uuid"] == uuid
    assert metadata["location"] == location
    assert metadata["properties"]["tm-e2e"] == "created"
    [schema] = [s for s in metadata["schemas"] if s["schema-id"] == metadata["current-schema-id"]]
    assert [[f["name"], f["type"], f["required"]] for f in schema["fields"]] == [
        ["id", "long", True],
        ["order_ts", "timestamptz", False],
    ]
    [spec] = [s for s in metadata["partition-specs"] if s["spec-id"] == metadata["default-spec-id"]]
    assert [f["transform"] for f in spec["fields"]] == ["day"]
    assert "rt_orders" in _names(api.get(tables))

    _ok(api.put(f"{tables}/rt_orders/properties", json={"expected_uuid": uuid, "updates": {"tm-e2e": "updated"}}))
    assert _ok(polaris.catalog("GET", f"{held_at}/rt_orders"))["metadata"]["properties"]["tm-e2e"] == "updated"
    stale = api.put(
        f"{tables}/rt_orders/properties",
        json={"expected_uuid": "00000000-0000-0000-0000-000000000000", "updates": {"tm-e2e": "stale"}},
    )
    assert stale.status_code == 409, stale.text
    assert stale.json()["detail"].endswith(RELOAD)

    _ok(
        api.post(
            f"{tables}/rt_orders/rename",
            json={"target_namespace": ["tm_e2e", "a.b"], "target_name": "rt_orders_renamed"},
        )
    )
    _gone(polaris.catalog("GET", f"{held_at}/rt_orders"), "the old name rt_orders")
    assert _ok(polaris.catalog("GET", f"{held_at}/rt_orders_renamed"))["metadata"]["table-uuid"] == uuid


def _generic_table_and_view(api: httpx.Client, polaris: PolarisClient, catalog: str, base: str) -> None:
    child = _ns("tm_e2e", "a.b")
    under = f"/v1/catalogs/{catalog}/namespaces/{child}"
    location = f"{base}/tm_e2e/a.b/rt_generic"
    _ok(
        api.post(
            f"{under}/generic-tables",
            json={
                "name": "rt_generic",
                "format": "delta",
                "base_location": location,
                "doc": "round trip",
                "properties": {"tm-e2e": "created"},
            },
        )
    )
    generic = _ok(polaris.catalog("GET", f"/polaris/v1/{catalog}/namespaces/{child}/generic-tables/rt_generic"))
    assert generic["table"]["format"] == "delta"
    assert generic["table"]["base-location"] == location
    assert generic["table"]["doc"] == "round trip"
    assert generic["table"]["properties"]["tm-e2e"] == "created"
    assert "rt_generic" in _names(api.get(f"{under}/generic-tables"))

    _ok(api.post(f"{under}/views", json={"name": "rt_view", "sql": "SELECT 1 AS one", "dialect": "spark"}))
    metadata = _ok(polaris.catalog("GET", f"/v1/{catalog}/namespaces/{child}/views/rt_view"))["metadata"]
    [version] = [v for v in metadata["versions"] if v["version-id"] == metadata["current-version-id"]]
    assert version["representations"] == [{"type": "sql", "sql": "SELECT 1 AS one", "dialect": "spark"}]
    [schema] = [s for s in metadata["schemas"] if s["schema-id"] == version["schema-id"]]
    assert schema["fields"] == []
    assert "rt_view" in _names(api.get(f"{under}/views"))


def _deletes(api: httpx.Client, polaris: PolarisClient, catalog: str) -> None:
    child = _ns("tm_e2e", "a.b")
    under = f"/v1/catalogs/{catalog}/namespaces/{child}"
    held_at = f"/v1/{catalog}/namespaces/{child}"
    ours = api.delete(under)
    theirs = polaris.catalog("DELETE", held_at)
    assert ours.status_code == theirs.status_code, (ours.text, theirs.text)
    assert ours.json()["detail"] == theirs.json()["error"]["message"]

    _ok(api.delete(f"{under}/views/rt_view"))
    _gone(polaris.catalog("GET", f"{held_at}/views/rt_view"), "view rt_view")
    _ok(api.delete(f"{under}/generic-tables/rt_generic"))
    _gone(
        polaris.catalog("GET", f"/polaris/v1/{catalog}/namespaces/{child}/generic-tables/rt_generic"),
        "generic table rt_generic",
    )
    _ok(api.delete(f"{under}/tables/rt_orders_renamed"))
    _gone(polaris.catalog("GET", f"{held_at}/tables/rt_orders_renamed"), "table rt_orders_renamed")
    _ok(api.delete(under))
    _gone(polaris.catalog("GET", held_at), "namespace [tm_e2e, a.b]")
    _ok(api.delete(f"/v1/catalogs/{catalog}/namespaces/tm_e2e"))
    _gone(polaris.catalog("GET", f"/v1/{catalog}/namespaces/tm_e2e"), "namespace [tm_e2e]")
    _ok(api.delete(f"/v1/catalogs/{catalog}"))
    _gone(polaris.management("GET", f"/catalogs/{catalog}"), f"catalog {catalog}")
