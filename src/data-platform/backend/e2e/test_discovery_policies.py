"""Discovery policies answer through the API: at least one rule, attaching needs a real place, saving versions.

A policy is attached to a place (a catalog, namespace or table) and detached from it by that place;
it cannot be deleted while it is attached anywhere. All of it is API answers, besides the catalog
scan an attach asks for; what a scan does with a policy is in the discovery lifecycle scenario. Each
scenario attaches only in a catalog of the module's own, so ``iceberg``'s scans are not changed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pyarrow as pa
import pytest

from e2e.support import OwnedNames, assert_prefixed_ids, drop_table, latest_run, wait_until, wait_until_unmanaged

if TYPE_CHECKING:
    import httpx
    from pyarrow import fs
    from temporalio.client import Client

    from e2e.support import CleanupStack, OwnedCatalog, PlatformApi, TemporalSession

pytestmark = pytest.mark.critical

POLICIES = "/v1/discovery-policies"
INCLUDE_ORDERS = {"action": "include", "table_name_pattern": "orders_*"}
EXCLUDE_TMP = {"action": "exclude", "table_name_pattern": "tmp_*"}
INCLUDE_SALES = {"action": "include", "table_name_pattern": "sales_*"}
ROWS = pa.schema([pa.field("id", pa.int64())])
DECIDE_SECONDS = 300


def _delete_if_present(api: httpx.Client, path: str) -> None:
    reply = api.delete(path)
    assert reply.status_code in (204, 404), f"DELETE {path} answered {reply.status_code}: {reply.text}"


def _create(platform: PlatformApi, api: httpx.Client, cleanup: CleanupStack, name: str, rules: list[dict]) -> dict:
    created = platform.call("POST", POLICIES, {"name": name, "description": "e2e", "rules": rules})
    cleanup.push(f"delete {name}", lambda: _delete_if_present(api, f"{POLICIES}/{name}"))
    return created


def _attach(platform: PlatformApi, api: httpx.Client, cleanup: CleanupStack, name: str, target: dict) -> httpx.Response:
    """Attach through the API as it answers, pushing the detach (fine when already detached) when it took."""
    reply = api.put(f"{POLICIES}/{name}/attachments", json={"target": target})
    if reply.is_success:
        cleanup.push(
            f"detach {name} from {target['type']}:{'.'.join(target['path'])}",
            lambda: platform.detach("discovery", name, target, missing_ok=True),
        )
    return reply


def _listed_unfailed(platform: PlatformApi, catalog: str) -> bool:
    """Whether ``catalog`` is listed as scanned with no current failure (its scan record is not read)."""
    found = [c for c in platform.get("/v1/scanned-catalogs")["catalogs"] if c["catalog"] == catalog]
    return bool(found) and found[0]["failure"] is None


def _places(platform: PlatformApi, name: str) -> list[tuple[str, list[str]]]:
    return [
        (found["target"]["type"], found["target"]["path"])
        for found in platform.get(f"{POLICIES}/{name}/attachments")["attachments"]
    ]


def test_a_policy_without_rules_is_refused(
    api: httpx.Client, platform: PlatformApi, suffix: str, cleanup: CleanupStack
):
    """A policy needs at least one rule, when it is created and when it is saved; nothing is stored by the refusal."""
    name = OwnedNames.discovery_policy(suffix, "norules")
    created = api.post(POLICIES, json={"name": name, "description": "e2e", "rules": []})
    assert created.status_code == 422, created.text
    assert api.get(f"{POLICIES}/{name}").status_code == 404

    _create(platform, api, cleanup, name, [INCLUDE_ORDERS])
    saved = api.put(f"{POLICIES}/{name}", json={"version": 1, "description": "e2e, emptied", "rules": []})
    assert saved.status_code == 422, saved.text
    kept = platform.get(f"{POLICIES}/{name}")
    assert (kept["version"], kept["rules"]) == (1, [INCLUDE_ORDERS])


def test_an_exclude_only_policy_is_accepted(
    api: httpx.Client, platform: PlatformApi, suffix: str, cleanup: CleanupStack
):
    """Exclude rules alone are a policy: it is stored at version 1 and answers its rule as written."""
    name = OwnedNames.discovery_policy(suffix, "excludeonly")
    created = _create(platform, api, cleanup, name, [EXCLUDE_TMP])
    assert (created["version"], created["rules"]) == (1, [EXCLUDE_TMP])
    assert_prefixed_ids({"dp": [created["id"]]})
    assert platform.get(f"{POLICIES}/{name}")["rules"] == [EXCLUDE_TMP]
    assert set(created) == {"id", "name", "version", "created_at", "updated_at", "description", "rules"}


def test_the_last_matching_rule_decides(
    platform: PlatformApi,
    api: httpx.Client,
    temporal: TemporalSession[Client],
    s3: fs.FileSystem,
    owned_catalog: OwnedCatalog,
    suffix: str,
    cleanup: CleanupStack,
):
    """Under include *, exclude *_tmp, include orders_tmp: a_tmp is left out, orders_tmp and orders are managed.

    A dry-run maintenance policy on the namespace keeps the managed tables from running anything.
    """
    catalog, namespace = owned_catalog.name, OwnedNames.namespace(suffix, "lastrule")
    owned_catalog.iceberg.create_namespace((namespace,))
    cleanup.push(f"drop {namespace}", lambda: owned_catalog.iceberg.drop_namespace((namespace,)))
    dry = OwnedNames.maintenance_policy(suffix, "lastrule")
    platform.create_maintenance_policy(dry, "e2e: dry run", lambda body: {**body, "dry_run": True})
    cleanup.push(f"delete {dry}", lambda: _delete_if_present(api, f"/v1/maintenance-policies/{dry}"))
    on_namespace = {"type": "namespace", "path": [catalog, namespace]}
    platform.attach("maintenance", dry, on_namespace)
    cleanup.push(f"detach {dry}", lambda: platform.detach("maintenance", dry, on_namespace, missing_ok=True))
    for table in ("a_tmp", "orders_tmp", "orders"):
        place = (namespace, table)
        owned_catalog.iceberg.create_table(place, ROWS)
        cleanup.push(f"drop {namespace}.{table}", lambda place=place: drop_table(owned_catalog.iceberg, s3, place))
        cleanup.push(
            f"wait until {namespace}.{table} is unmanaged",
            lambda table=table: wait_until_unmanaged(platform, temporal, (catalog, namespace, table)),
        )
    name = OwnedNames.discovery_policy(suffix, "lastrule")
    rules = [
        {"action": "include", "table_name_pattern": "*"},
        {"action": "exclude", "table_name_pattern": "*_tmp"},
        {"action": "include", "table_name_pattern": "orders_tmp"},
    ]
    policy = _create(platform, api, cleanup, name, rules)
    assert policy["rules"] == rules
    platform.attach("discovery", name, on_namespace)
    cleanup.push(f"detach {name}", lambda: platform.detach("discovery", name, on_namespace, missing_ok=True))

    expected = {"a_tmp": ("unmanaged", 2), "orders_tmp": ("managed", 3), "orders": ("managed", 1)}

    def decided() -> dict[str, dict]:
        found = {table: platform.table(catalog, namespace, table) for table in expected}
        seen = {table: (row["status"], row["decided_by"]) if row else None for table, row in found.items()}
        wanted = {
            table: (status, {"policy_id": policy["id"], "policy_version": 1, "rule_position": position})
            for table, (status, position) in expected.items()
        }
        if seen != wanted:
            raise AssertionError(seen)
        return {table: row for table, row in found.items() if row}

    wait_until(decided, timeout=DECIDE_SECONDS, interval=3, what=f"{namespace} decided by {name}")
    for table, (_, position) in expected.items():
        row = platform.table(catalog, namespace, table)
        assert row is not None
        assert platform.get(f"/v1/tables/{row['uuid']}")["decided_by"]["rule_position"] == position, table


def test_a_policy_attaches_to_an_empty_namespace_and_never_to_a_missing_place(
    api: httpx.Client,
    platform: PlatformApi,
    temporal: TemporalSession[Client],
    owned_catalog: OwnedCatalog,
    suffix: str,
    cleanup: CleanupStack,
):
    """An empty namespace may hold a policy and its catalog is then scanned; a missing place is 404, a dot 422.

    The attach answers the place and the policy, with no id of its own; the refusals store nothing and
    start no scan.
    """
    name = OwnedNames.discovery_policy(suffix, "attach")
    policy = _create(platform, api, cleanup, name, [INCLUDE_ORDERS])
    namespace = OwnedNames.namespace(suffix, "attach")
    platform.call("POST", f"/v1/catalogs/{owned_catalog.name}/namespaces", {"namespace": [namespace]})
    cleanup.push(
        f"drop {namespace}",
        lambda: _delete_if_present(api, f"/v1/catalogs/{owned_catalog.name}/namespaces/{namespace}"),
    )

    target = {"type": "namespace", "path": [owned_catalog.name, namespace]}
    attached = _attach(platform, api, cleanup, name, target)
    assert attached.status_code == 200, attached.text
    assert attached.json() == {
        "target": target | {"table_uuid": None},
        "policy_id": policy["id"],
        "policy_name": name,
    }
    assert _places(platform, name) == [("namespace", [owned_catalog.name, namespace])]
    assert _listed_unfailed(platform, owned_catalog.name), "a catalog holding a discovery policy is scanned"

    missing_catalog = OwnedNames.catalog(suffix, "missing")
    for refused_target, status in (
        ({"type": "namespace", "path": [owned_catalog.name, "no_such_ns"]}, 404),
        ({"type": "catalog", "path": [missing_catalog]}, 404),
        ({"type": "namespace", "path": [owned_catalog.name, f"{namespace}.child"]}, 422),
    ):
        refused = _attach(platform, api, cleanup, name, refused_target)
        assert refused.status_code == status, f"{refused_target}: {refused.status_code} {refused.text}"
        assert refused.json()["detail"], refused.text
    assert _places(platform, name) == [("namespace", [owned_catalog.name, namespace])]
    assert latest_run(temporal, f"table-discovery:catalog={missing_catalog}") is None

    platform.detach("discovery", name, target)
    assert _places(platform, name) == []
    again = api.delete(f"{POLICIES}/{name}/attachments", params={"target_type": "namespace", "path": target["path"]})
    assert again.status_code == 404, again.text


def test_saving_a_policy_makes_a_version(api: httpx.Client, platform: PlatformApi, suffix: str, cleanup: CleanupStack):
    """A save makes version 2 and keeps version 1 readable; a stale save is 409 and changes nothing."""
    name = OwnedNames.discovery_policy(suffix, "versions")
    first = _create(platform, api, cleanup, name, [INCLUDE_ORDERS, EXCLUDE_TMP])
    assert first["version"] == 1
    assert_prefixed_ids({"dp": [first["id"]]})

    update: dict[str, Any] = {
        "version": 1,
        "description": "e2e, saved",
        "rules": [EXCLUDE_TMP, INCLUDE_ORDERS, INCLUDE_SALES],
    }
    second = platform.call("PUT", f"{POLICIES}/{name}", update)
    assert second["version"] == 2
    assert second["id"] == first["id"]
    assert second["rules"] == update["rules"]

    original = platform.get(f"{POLICIES}/{name}/versions/1")
    assert (original["version"], original["description"], original["rules"]) == (1, "e2e", first["rules"])
    stale = api.put(f"{POLICIES}/{name}", json=update)
    assert stale.status_code == 409, stale.text
    assert platform.get(f"{POLICIES}/{name}")["version"] == 2


def test_a_policy_in_use_cannot_be_deleted(
    api: httpx.Client, platform: PlatformApi, owned_catalog: OwnedCatalog, suffix: str, cleanup: CleanupStack
):
    """Deleting a policy still attached is 409 naming each place it is on; once detached from all, it deletes."""
    name = OwnedNames.discovery_policy(suffix, "inuse")
    _create(platform, api, cleanup, name, [INCLUDE_ORDERS])
    namespace = OwnedNames.namespace(suffix, "inuse")
    owned_catalog.iceberg.create_namespace((namespace,))
    cleanup.push(f"drop {namespace}", lambda: owned_catalog.iceberg.drop_namespace((namespace,)))
    on_catalog = {"type": "catalog", "path": [owned_catalog.name]}
    on_namespace = {"type": "namespace", "path": [owned_catalog.name, namespace]}
    for target in (on_catalog, on_namespace):
        attached = _attach(platform, api, cleanup, name, target)
        assert attached.status_code == 200, attached.text

    refused = api.delete(f"{POLICIES}/{name}")
    assert refused.status_code == 409, refused.text
    detail = refused.json()["detail"]
    assert detail.startswith(f"discovery policy {name} is still attached to "), detail
    named = sorted(detail.removeprefix(f"discovery policy {name} is still attached to ").split(", "))
    assert named == [f"catalog:{owned_catalog.name}", f"namespace:{owned_catalog.name}.{namespace}"], detail

    platform.detach("discovery", name, on_catalog)
    still = api.delete(f"{POLICIES}/{name}")
    assert still.status_code == 409, still.text
    assert still.json()["detail"] == (
        f"discovery policy {name} is still attached to namespace:{owned_catalog.name}.{namespace}"
    )
    platform.detach("discovery", name, on_namespace)
    deleted = api.delete(f"{POLICIES}/{name}")
    assert deleted.status_code == 204, deleted.text
    assert api.get(f"{POLICIES}/{name}").status_code == 404
