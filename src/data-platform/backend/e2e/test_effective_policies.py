"""What applies at a place in the catalog: the nearest policy of each kind, or the defaults that exist.

The tables live in a catalog of the module's own and are never managed: the discovery policy has only
an ``exclude`` rule, so nothing is managed and the answers come from the places policies are attached to.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pyarrow as pa
import pytest
from pyiceberg.exceptions import NoSuchNamespaceError

from e2e.support import OwnedNames, assert_prefixed_ids, drop_table, wait_until

if TYPE_CHECKING:
    import httpx
    from pyarrow import fs

    from e2e.support import CleanupStack, OwnedCatalog, PlatformApi

pytestmark = pytest.mark.critical

MAINTENANCE = "/v1/maintenance-policies"
DISCOVERY = "/v1/discovery-policies"
ROWS = pa.schema([pa.field("id", pa.int64())])
ORPHAN_SECONDS = 120


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


def _attach(platform: PlatformApi, cleanup: CleanupStack, kind: str, name: str, path: list[str]) -> dict:
    """Attach to the catalog, namespace or table ``path`` names (by its length) and push the detach."""
    target = {"type": ("catalog", "namespace", "table")[len(path) - 1], "path": path}
    platform.attach(kind, name, target)
    cleanup.push(f"detach {name}", lambda: platform.detach(kind, name, target, missing_ok=True))
    return target


def _effective(platform: PlatformApi, catalog: str, **place: str) -> tuple[dict, dict]:
    maintenance, discovery = platform.get("/v1/effective-policies", catalog=catalog, **place)["policies"]
    assert (maintenance["kind"], discovery["kind"]) == ("maintenance", "discovery")
    return maintenance, discovery


def test_the_nearest_policy_of_each_kind_applies_and_detaching_falls_back(
    api: httpx.Client,
    platform: PlatformApi,
    s3: fs.FileSystem,
    owned_catalog: OwnedCatalog,
    suffix: str,
    cleanup: CleanupStack,
):
    """A table's own maintenance policy wins over its namespace's; its sibling and discovery keep theirs."""
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
            "rules": [{"action": "exclude", "table_name_pattern": "*"}],
        },
    )
    cleanup.push(f"delete {discovery}", lambda: _delete_if_present(api, f"{DISCOVERY}/{discovery}"))
    namespace_target = _attach(platform, cleanup, "maintenance", on_namespace, [catalog, namespace])
    table_target = _attach(platform, cleanup, "maintenance", on_table, [catalog, namespace, "a"])
    _attach(platform, cleanup, "discovery", discovery, [catalog, namespace])

    own, found = _effective(platform, catalog, namespace=namespace, table="a")
    assert (own["policy_name"], own["dry_run"], own["version"]) == (on_table, True, 1)
    assert_prefixed_ids({"mp": [own["policy_id"]]})
    a_uuid = str(owned_catalog.iceberg.load_table((namespace, "a")).metadata.table_uuid)
    assert own["target"] == {"type": "table", "path": [catalog, namespace, "a"], "table_uuid": a_uuid}
    sibling, sibling_found = _effective(platform, catalog, namespace=namespace, table="b")
    assert (sibling["policy_name"], sibling["dry_run"]) == (on_namespace, False)
    assert sibling["target"] == {"type": "namespace", "path": [catalog, namespace], "table_uuid": None}
    for answer in (own, found, sibling, sibling_found):
        assert "attachment_id" not in answer, answer
    for answer in (found, sibling_found):
        assert (answer["policy_name"], answer["version"]) == (discovery, 1)
        assert_prefixed_ids({"dp": [answer["policy_id"]]})
        assert answer["target"] == {"type": "namespace", "path": [catalog, namespace], "table_uuid": None}

    wrong_policy = api.delete(
        f"{MAINTENANCE}/{on_table}/attachments", params={"target_type": "namespace", "path": [catalog, namespace]}
    )
    assert wrong_policy.status_code == 404, wrong_policy.text
    malformed = api.delete(f"{MAINTENANCE}/{on_table}/attachments", params={"target_type": "schema", "path": [catalog]})
    assert malformed.status_code == 422, malformed.text
    platform.detach("maintenance", on_table, table_target)
    fallen_back, _ = _effective(platform, catalog, namespace=namespace, table="a")
    assert fallen_back["policy_name"] == on_namespace
    assert fallen_back["target"] == namespace_target | {"table_uuid": None}
    platform.attach("maintenance", on_namespace, namespace_target)
    [listed] = platform.get(f"{MAINTENANCE}/{on_namespace}/attachments")["attachments"]
    assert listed["target"] == namespace_target | {"table_uuid": None}, "attaching again is the same one place"


def test_a_place_with_nothing_attached_gets_the_maintenance_default_and_no_discovery_policy(
    platform: PlatformApi, owned_catalog: OwnedCatalog, suffix: str, cleanup: CleanupStack
):
    """The catalog and a nested namespace (dot-joined) get the maintenance default and no discovery policy at all."""
    parent = OwnedNames.namespace(suffix, "defaults")
    _namespace(owned_catalog, cleanup, (parent,))
    _namespace(owned_catalog, cleanup, (parent, "child"))
    for place in ({}, {"namespace": f"{parent}.child"}):
        maintenance, discovery = _effective(platform, owned_catalog.name, **place)
        assert (maintenance["policy_name"], maintenance["target"]) == ("default", None), place
        assert "attachment_id" not in maintenance, maintenance
        assert discovery == {
            "kind": "discovery",
            "policy_id": None,
            "policy_name": None,
            "version": None,
            "description": None,
            "target": None,
        }, place


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


def test_a_dropped_table_lets_go_of_its_policy_and_a_dropped_namespace_is_orphaned_until_detached(
    api: httpx.Client,
    platform: PlatformApi,
    s3: fs.FileSystem,
    owned_catalog: OwnedCatalog,
    suffix: str,
    cleanup: CleanupStack,
):
    """A table's uuid never comes back, so a dropped table holds no policy; a gone namespace keeps its own.

    Once the platform hears the table is gone (its drop reaches the platform as a catalog event, which
    asks for a scan), the policy is no longer listed on it. The namespace, dropped next, stays listed
    ``orphaned``, the policy cannot be deleted while it is, and detaching it (which does not read the
    catalog) works.
    """
    namespace = OwnedNames.namespace(suffix, "orphaned")
    owned_catalog.iceberg.create_namespace((namespace,))
    cleanup.push(f"drop {namespace}", lambda: _drop_namespace_if_present(owned_catalog, namespace))
    _table(owned_catalog, s3, cleanup, namespace, "gone")
    name = OwnedNames.maintenance_policy(suffix, "orphaned")
    _maintenance(platform, api, cleanup, name, dry_run=True)
    _attach(platform, cleanup, "maintenance", name, [owned_catalog.name, namespace, "gone"])
    on_namespace = _attach(platform, cleanup, "maintenance", name, [owned_catalog.name, namespace])
    listed = _listed(platform, name)
    assert listed == {("table", namespace): False, ("namespace", namespace): False}, listed

    drop_table(owned_catalog.iceberg, s3, (namespace, "gone"))
    wait_until(
        lambda: _listed_as(platform, name, {("namespace", namespace): False}),
        timeout=ORPHAN_SECONDS,
        interval=2,
        what=f"{name} let go by the dropped table (a catalog event, then a scan)",
    )
    owned_catalog.iceberg.drop_namespace((namespace,))
    wait_until(
        lambda: _listed_as(platform, name, {("namespace", namespace): True}),
        timeout=ORPHAN_SECONDS,
        interval=2,
        what=f"{name}'s namespace listed orphaned",
    )
    refused = api.delete(f"{MAINTENANCE}/{name}")
    assert refused.status_code == 409, refused.text
    assert refused.json()["detail"] == (
        f"maintenance policy {name} is still attached to namespace:{owned_catalog.name}.{namespace}"
    )
    platform.detach("maintenance", name, on_namespace)
    assert platform.get(f"{MAINTENANCE}/{name}/attachments")["attachments"] == []


def _listed(platform: PlatformApi, name: str) -> dict[tuple[str, str], bool]:
    """Return each place the policy is listed on as ``(type, namespace)``, with whether it is orphaned."""
    return {
        (found["target"]["type"], found["target"]["path"][1]): found["orphaned"]
        for found in platform.get(f"{MAINTENANCE}/{name}/attachments")["attachments"]
    }


def _listed_as(platform: PlatformApi, name: str, expected: dict[tuple[str, str], bool]) -> bool:
    """Return True once the policy is listed on exactly ``expected``; raise with what it is listed on until then."""
    listed = _listed(platform, name)
    if listed != expected:
        raise AssertionError(listed)
    return True


def _drop_namespace_if_present(owned: OwnedCatalog, namespace: str) -> None:
    try:
        owned.iceberg.drop_namespace((namespace,))
    except NoSuchNamespaceError:
        return
