"""Discovery policies answer through the API: at least one rule, attaching needs a real place, saving versions.

All of it is API answers; what a scan then does with a policy is in the discovery lifecycle scenario.
Each scenario attaches only in a catalog of the module's own, so ``iceberg``'s scans are not changed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pyarrow as pa
import pytest

from e2e.support import OwnedNames, assert_prefixed_ids, drop_table, schedule_exists, wait_until, wait_until_unmanaged

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


def _attach(api: httpx.Client, cleanup: CleanupStack, name: str, target: dict) -> httpx.Response:
    reply = api.put(f"{POLICIES}/{name}/attachments", json={"target": target})
    if reply.is_success:
        path = f"{POLICIES}/{name}/attachments/{reply.json()['id']}"
        cleanup.push(f"detach {name} from {target['path']}", lambda: _delete_if_present(api, path))
    return reply


def _attachment_ids(platform: PlatformApi, name: str) -> list[str]:
    return [attachment["id"] for attachment in platform.get(f"{POLICIES}/{name}/attachments")["attachments"]]


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
    dry_attachment = platform.attach("maintenance-policies", dry, {"type": "namespace", "path": [catalog, namespace]})
    cleanup.push(
        f"detach {dry}",
        lambda: _delete_if_present(api, f"/v1/maintenance-policies/{dry}/attachments/{dry_attachment}"),
    )
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
    attachment = platform.attach("discovery-policies", name, {"type": "namespace", "path": [catalog, namespace]})
    cleanup.push(f"detach {name}", lambda: _delete_if_present(api, f"{POLICIES}/{name}/attachments/{attachment}"))

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
    """An empty namespace may hold an attachment; a missing namespace or catalog is 404 and stores nothing."""
    name = OwnedNames.discovery_policy(suffix, "attach")
    _create(platform, api, cleanup, name, [INCLUDE_ORDERS])
    namespace = OwnedNames.namespace(suffix, "attach")
    platform.call("POST", f"/v1/catalogs/{owned_catalog.name}/namespaces", {"namespace": [namespace]})
    cleanup.push(
        f"drop {namespace}",
        lambda: _delete_if_present(api, f"/v1/catalogs/{owned_catalog.name}/namespaces/{namespace}"),
    )

    attached = _attach(api, cleanup, name, {"type": "namespace", "path": [owned_catalog.name, namespace]})
    assert attached.status_code == 200, attached.text
    assert_prefixed_ids({"da": [attached.json()["id"]]})
    assert _attachment_ids(platform, name) == [attached.json()["id"]]
    owned_schedule = f"table-discovery:catalog={owned_catalog.name}"
    wait_until(
        lambda: schedule_exists(temporal, owned_schedule) or None,
        timeout=60,
        interval=2,
        what=f"{owned_schedule} created",
    )

    missing_catalog = OwnedNames.catalog(suffix, "missing")
    for target in (
        {"type": "namespace", "path": [owned_catalog.name, "no_such_ns"]},
        {"type": "catalog", "path": [missing_catalog]},
    ):
        refused = _attach(api, cleanup, name, target)
        assert refused.status_code == 404, f"{target}: {refused.status_code} {refused.text}"
        assert refused.json()["detail"], refused.text
    assert _attachment_ids(platform, name) == [attached.json()["id"]]
    assert not schedule_exists(temporal, f"table-discovery:catalog={missing_catalog}")


def test_saving_a_policy_makes_a_version(
    api: httpx.Client, platform: PlatformApi, owned_catalog: OwnedCatalog, suffix: str, cleanup: CleanupStack
):
    """A save makes version 2 and keeps version 1 readable; a stale save and deleting an attached policy are 409."""
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

    attached = _attach(api, cleanup, name, {"type": "catalog", "path": [owned_catalog.name]})
    assert attached.status_code == 200, attached.text
    refused = api.delete(f"{POLICIES}/{name}")
    assert refused.status_code == 409, refused.text
    platform.call("DELETE", f"{POLICIES}/{name}/attachments/{attached.json()['id']}")
    deleted = api.delete(f"{POLICIES}/{name}")
    assert deleted.status_code == 204, deleted.text
    assert api.get(f"{POLICIES}/{name}").status_code == 404
