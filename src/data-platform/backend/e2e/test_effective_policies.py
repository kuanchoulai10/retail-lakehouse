"""What applies at a place in the catalog: the nearest attachment of each kind, or the platform default.

The tables live in a catalog of the module's own and are never managed: the discovery policy has only
an ``unmanage`` rule, so nothing scans them and the answers come from attachments alone.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pyarrow as pa
import pytest

from e2e.support import OwnedNames, assert_prefixed_ids, drop_table, wait_until

if TYPE_CHECKING:
    import httpx
    from pyarrow import fs

    from e2e.support import CleanupStack, OwnedCatalog, PlatformApi

pytestmark = pytest.mark.critical

MAINTENANCE = "/v1/maintenance-policies"
DISCOVERY = "/v1/discovery-policies"
ROWS = pa.schema([pa.field("id", pa.int64())])


def _delete_if_present(api: httpx.Client, path: str) -> None:
    reply = api.delete(path)
    assert reply.status_code in (204, 404), f"DELETE {path} answered {reply.status_code}: {reply.text}"


def _namespace(owned: OwnedCatalog, cleanup: CleanupStack, namespace: tuple[str, ...]) -> None:
    owned.iceberg.create_namespace(namespace)
    cleanup.push(f"drop {'.'.join(namespace)}", lambda: owned.iceberg.drop_namespace(namespace))


def _table(owned: OwnedCatalog, s3: fs.FileSystem, cleanup: CleanupStack, namespace: str, table: str) -> None:
    owned.iceberg.create_table((namespace, table), ROWS)
    cleanup.push(f"drop {namespace}.{table}", lambda: drop_table(owned.iceberg, s3, (namespace, table)))


def _maintenance(platform: PlatformApi, api: httpx.Client, cleanup: CleanupStack, name: str, dry_run: bool) -> dict:
    created = platform.create_maintenance_policy(name, "e2e", lambda body: {**body, "dry_run": dry_run})
    cleanup.push(f"delete {name}", lambda: _delete_if_present(api, f"{MAINTENANCE}/{name}"))
    return created


def _attach(
    platform: PlatformApi, api: httpx.Client, cleanup: CleanupStack, kind: str, name: str, path: list[str]
) -> str:
    target = {"type": ("catalog", "namespace", "table")[len(path) - 1], "path": path}
    attachment = platform.attach(kind, name, target)
    cleanup.push(f"detach {name}", lambda: _delete_if_present(api, f"/v1/{kind}/{name}/attachments/{attachment}"))
    return attachment


def _effective(platform: PlatformApi, catalog: str, **place: str) -> tuple[dict, dict]:
    maintenance, discovery = platform.get("/v1/effective-policies", catalog=catalog, **place)["policies"]
    assert (maintenance["kind"], discovery["kind"]) == ("maintenance", "discovery")
    return maintenance, discovery


def test_the_nearest_attachment_of_each_kind_applies_and_detaching_falls_back(
    api: httpx.Client,
    platform: PlatformApi,
    s3: fs.FileSystem,
    owned_catalog: OwnedCatalog,
    suffix: str,
    cleanup: CleanupStack,
):
    """A table's own maintenance attachment wins over its namespace's; its sibling and discovery keep theirs."""
    catalog, namespace = owned_catalog.name, OwnedNames.namespace(suffix, "nearest")
    _namespace(owned_catalog, cleanup, (namespace,))
    _table(owned_catalog, s3, cleanup, namespace, "a")
    _table(owned_catalog, s3, cleanup, namespace, "b")
    on_namespace, on_table = OwnedNames.maintenance_policy(suffix, "ns"), OwnedNames.maintenance_policy(suffix, "table")
    _maintenance(platform, api, cleanup, on_namespace, dry_run=False)
    _maintenance(platform, api, cleanup, on_table, dry_run=True)
    discovery = OwnedNames.discovery_policy(suffix, "nearest")
    platform.call(
        "POST",
        DISCOVERY,
        {
            "name": discovery,
            "description": "e2e: never manages",
            "no_match_outcome": "unmanage",
            "rules": [
                {
                    "outcome": "unmanage",
                    "conditions": [{"attribute": "table_name", "operator": "glob", "values": ["*"]}],
                }
            ],
        },
    )
    cleanup.push(f"delete {discovery}", lambda: _delete_if_present(api, f"{DISCOVERY}/{discovery}"))
    namespace_attachment = _attach(platform, api, cleanup, "maintenance-policies", on_namespace, [catalog, namespace])
    table_attachment = _attach(platform, api, cleanup, "maintenance-policies", on_table, [catalog, namespace, "a"])
    discovery_attachment = _attach(platform, api, cleanup, "discovery-policies", discovery, [catalog, namespace])
    assert_prefixed_ids({"pa": [namespace_attachment, table_attachment], "da": [discovery_attachment]})

    own, found = _effective(platform, catalog, namespace=namespace, table="a")
    assert (own["policy_name"], own["dry_run"], own["version"]) == (on_table, True, 1)
    a_uuid = str(owned_catalog.iceberg.load_table((namespace, "a")).metadata.table_uuid)
    assert own["target"] == {"type": "table", "path": [catalog, namespace, "a"], "table_uuid": a_uuid}
    assert own["attachment_id"] == table_attachment
    sibling, sibling_found = _effective(platform, catalog, namespace=namespace, table="b")
    assert (sibling["policy_name"], sibling["dry_run"]) == (on_namespace, False)
    assert (sibling["target"], sibling["attachment_id"]) == (
        {"type": "namespace", "path": [catalog, namespace], "table_uuid": None},
        namespace_attachment,
    )
    for answer in (found, sibling_found):
        assert (answer["policy_name"], answer["no_match_outcome"], answer["attachment_id"]) == (
            discovery,
            "unmanage",
            discovery_attachment,
        )
        assert answer["target"] == {"type": "namespace", "path": [catalog, namespace], "table_uuid": None}

    wrong_policy = api.delete(f"{MAINTENANCE}/{on_table}/attachments/{namespace_attachment}")
    assert wrong_policy.status_code == 404, wrong_policy.text
    malformed = api.delete(f"{MAINTENANCE}/{on_table}/attachments/not-an-id")
    assert malformed.status_code == 422, malformed.text
    platform.call("DELETE", f"{MAINTENANCE}/{on_table}/attachments/{table_attachment}")
    fallen_back, _ = _effective(platform, catalog, namespace=namespace, table="a")
    assert (fallen_back["policy_name"], fallen_back["attachment_id"]) == (on_namespace, namespace_attachment)
    again = platform.attach("maintenance-policies", on_namespace, {"type": "namespace", "path": [catalog, namespace]})
    assert again == namespace_attachment


def test_a_place_with_nothing_attached_gets_both_platform_defaults(
    platform: PlatformApi, owned_catalog: OwnedCatalog, suffix: str, cleanup: CleanupStack
):
    """The catalog and a nested namespace (dot-joined) fall back to the defaults, with no target and no attachment."""
    parent = OwnedNames.namespace(suffix, "defaults")
    _namespace(owned_catalog, cleanup, (parent,))
    _namespace(owned_catalog, cleanup, (parent, "child"))
    for place in ({}, {"namespace": f"{parent}.child"}):
        for answer in _effective(platform, owned_catalog.name, **place):
            assert (answer["policy_name"], answer["target"], answer["attachment_id"]) == ("default", None, None), place


def test_a_place_the_catalog_does_not_hold_is_not_found(
    api: httpx.Client, owned_catalog: OwnedCatalog, suffix: str, cleanup: CleanupStack
):
    """A missing namespace, catalog or table, and a table uuid maintenance has no record of, are 404."""
    namespace = OwnedNames.namespace(suffix, "missing")
    _namespace(owned_catalog, cleanup, (namespace,))
    for place in (
        {"catalog": owned_catalog.name, "namespace": "no_such_ns"},
        {"catalog": OwnedNames.catalog(suffix, "missing")},
        {"catalog": owned_catalog.name, "namespace": namespace, "table": "no_such_table"},
    ):
        reply = api.get("/v1/effective-policies", params=place)
        assert reply.status_code == 404, f"{place}: {reply.status_code} {reply.text}"
        assert reply.json() != {"detail": "Not Found"}, f"{place}: no route answered, not the handler"
    unknown = api.get("/v1/tables/00000000-0000-4000-8000-000000000000/effective-policies")
    assert unknown.status_code == 404, unknown.text
    assert unknown.json() != {"detail": "Not Found"}, "no route answered, not the handler"


def test_an_attachment_whose_table_was_dropped_is_orphaned_and_still_detaches(
    api: httpx.Client,
    platform: PlatformApi,
    s3: fs.FileSystem,
    owned_catalog: OwnedCatalog,
    suffix: str,
    cleanup: CleanupStack,
):
    """The list marks it ``orphaned`` once the platform hears the table is gone, and detaching it by id still works."""
    namespace = OwnedNames.namespace(suffix, "orphaned")
    _namespace(owned_catalog, cleanup, (namespace,))
    _table(owned_catalog, s3, cleanup, namespace, "gone")
    name = OwnedNames.maintenance_policy(suffix, "orphaned")
    _maintenance(platform, api, cleanup, name, dry_run=True)
    attachment = _attach(platform, api, cleanup, "maintenance-policies", name, [owned_catalog.name, namespace, "gone"])
    [listed] = platform.get(f"{MAINTENANCE}/{name}/attachments")["attachments"]
    assert (listed["id"], listed["orphaned"]) == (attachment, False)

    drop_table(owned_catalog.iceberg, s3, (namespace, "gone"))
    [listed] = wait_until(
        lambda: (
            [found for found in platform.get(f"{MAINTENANCE}/{name}/attachments")["attachments"] if found["orphaned"]]
            or None
        ),
        timeout=60,
        interval=2,
        what=f"{name}'s attachment orphaned (the drop reaches the platform as a catalog event)",
    )
    assert listed["id"] == attachment
    platform.call("DELETE", f"{MAINTENANCE}/{name}/attachments/{attachment}")
    assert platform.get(f"{MAINTENANCE}/{name}/attachments")["attachments"] == []
