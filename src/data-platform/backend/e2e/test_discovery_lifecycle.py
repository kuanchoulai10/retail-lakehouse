"""Discovery manages what the nearest attachment says, and stops what it no longer says.

One lifecycle in a catalog of the module's own: attaching an including policy schedules and scans the
catalog, a table-level attachment of an exclude-only policy unmanages one table, a save that excludes a
managed table unmanages it, a save that matches nothing unmanages the rest, and detaching retires the
schedule. A second scenario puts an exclude-only policy on a namespace under a catalog-level include.
Marked ``full``: each step waits for scans and reconciliations.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

import pyarrow as pa
import pytest

from e2e.support import (
    OwnedNames,
    drop_table,
    reconciliation_running,
    schedule_exists,
    signals_received,
    wait_until,
    wait_until_unmanaged,
)

if TYPE_CHECKING:
    import httpx
    from pyarrow import fs
    from temporalio.client import Client

    from e2e.support import CleanupStack, OwnedCatalog, PlatformApi, TemporalSession

pytestmark = pytest.mark.full

POLICIES = "/v1/discovery-policies"
ROWS = pa.schema([pa.field("id", pa.int64())])
MANAGED = ("t1", "t2", "t3")
SETTLE_SECONDS = 180
# A stop ends a reconciliation only once its run is finished. Each managed table's first plan
# starts a remove_orphan_files run, and the normal queue admits one job at a time, so the last of
# the four tables' jobs can end several minutes after its stop.
STOP_SECONDS = 600


def _rule(action: str, pattern: str) -> dict:
    return {"action": action, "table_name_pattern": pattern}


def _delete_if_present(api: httpx.Client, path: str) -> None:
    reply = api.delete(path)
    assert reply.status_code in (204, 404), f"DELETE {path} answered {reply.status_code}: {reply.text}"


def _settle(
    platform: PlatformApi, catalog: str, statuses: dict[str, str], namespaces: tuple[str, ...]
) -> dict[str, dict]:
    """Wait until the tables of these namespaces (``namespace.table``) have exactly these statuses, and return them."""

    def settled() -> dict[str, dict]:
        tables = {
            f"{t['namespace']}.{t['table']}": t
            for t in platform.get("/v1/tables")
            if t["catalog"] == catalog and t["namespace"] in namespaces
        }
        seen = {key: table["status"] for key, table in tables.items()}
        if seen != statuses:
            raise AssertionError(seen)
        return tables

    return wait_until(settled, timeout=SETTLE_SECONDS, interval=3, what=f"tables of {catalog} {statuses}")


def _wait_stopped(temporal: TemporalSession[Client], table_uuid: str) -> None:
    workflow = f"table-reconciliation:table-uuid={table_uuid}"

    def stopped() -> bool:
        if "stop" not in signals_received(temporal, workflow) or reconciliation_running(temporal, table_uuid):
            raise AssertionError(f"{workflow}: {signals_received(temporal, workflow)}")
        return True

    wait_until(stopped, timeout=STOP_SECONDS, interval=3, what=f"{workflow} stopped")


def _decided_by(policy: dict, version: int, position: int | None) -> dict:
    return {"policy_id": policy["id"], "policy_version": version, "rule_position": position}


def _tables(
    owned: OwnedCatalog,
    platform: PlatformApi,
    temporal: TemporalSession[Client],
    s3: fs.FileSystem,
    cleanup: CleanupStack,
    namespace: str,
    tables: tuple[str, ...],
) -> None:
    owned.iceberg.create_namespace((namespace,))
    cleanup.push(f"drop {namespace}", lambda: owned.iceberg.drop_namespace((namespace,)))
    for table in tables:
        place = (namespace, table)
        owned.iceberg.create_table(place, ROWS)
        cleanup.push(f"drop {namespace}.{table}", lambda place=place: drop_table(owned.iceberg, s3, place))
        cleanup.push(
            f"wait until {namespace}.{table} is unmanaged",
            lambda place=place: wait_until_unmanaged(platform, temporal, (owned.name, place[0], place[1])),
        )


def _create(platform: PlatformApi, api: httpx.Client, cleanup: CleanupStack, name: str, rules: list[dict]) -> dict:
    created = platform.call("POST", POLICIES, {"name": name, "description": "e2e", "rules": rules})
    cleanup.push(f"delete {name}", lambda: _delete_if_present(api, f"{POLICIES}/{name}"))
    return created


def _attach(platform: PlatformApi, api: httpx.Client, cleanup: CleanupStack, name: str, target: dict) -> str:
    attachment = platform.attach("discovery-policies", name, target)
    cleanup.push(f"detach {name}", lambda: _delete_if_present(api, f"{POLICIES}/{name}/attachments/{attachment}"))
    return attachment


def _save(platform: PlatformApi, name: str, description: str, rules: list[dict]) -> dict:
    version = platform.get(f"{POLICIES}/{name}")["version"]
    body = {"version": version, "description": description, "rules": rules}
    return platform.call("PUT", f"{POLICIES}/{name}", body)


def test_discovery_manages_what_the_nearest_attachment_says(
    api: httpx.Client,
    platform: PlatformApi,
    temporal: TemporalSession[Client],
    s3: fs.FileSystem,
    owned_catalog: OwnedCatalog,
    suffix: str,
    cleanup: CleanupStack,
):
    """Attach, attach an exclude-only policy nearer, exclude a managed table, match nothing, restore, detach."""
    catalog = owned_catalog.name
    attached, other = OwnedNames.namespace(suffix, "attached"), OwnedNames.namespace(suffix, "other")
    _tables(owned_catalog, platform, temporal, s3, cleanup, attached, MANAGED)
    _tables(owned_catalog, platform, temporal, s3, cleanup, other, ("x",))
    place = (attached, other)
    name = OwnedNames.discovery_policy(suffix, "lifecycle")
    policy = _create(platform, api, cleanup, name, [_rule("include", "t*")])
    attachment = _attach(platform, api, cleanup, name, {"type": "namespace", "path": [catalog, attached]})

    everything = {f"{attached}.{table}": "managed" for table in MANAGED} | {f"{other}.x": "unmanaged"}
    tables = _settle(platform, catalog, everything, place)
    for table in MANAGED:
        assert tables[f"{attached}.{table}"]["decided_by"] == _decided_by(policy, 1, 1)
    assert tables[f"{other}.x"]["decided_by"] is None
    schedule = f"table-discovery:catalog={catalog}"
    assert schedule_exists(temporal, schedule)

    async def interval(client: Client) -> timedelta:
        described = await client.get_schedule_handle(schedule).describe()
        [every] = described.schedule.spec.intervals
        return every.every

    assert temporal.run(interval) == timedelta(seconds=platform.platform_setting("discovery_interval_seconds"))
    scanned = {found["catalog"]: found for found in platform.get("/v1/scanned-catalogs")["catalogs"]}
    assert scanned[catalog]["failure"] is None and scanned[catalog]["last_discovered_at"], scanned.get(catalog)

    nearer_name = OwnedNames.discovery_policy(suffix, "lifecycle_nearer")
    nearer = _create(platform, api, cleanup, nearer_name, [_rule("exclude", "*")])
    on_t1 = _attach(platform, api, cleanup, nearer_name, {"type": "table", "path": [catalog, attached, "t1"]})
    assert on_t1 in [found["id"] for found in platform.get(f"{POLICIES}/{nearer_name}/attachments")["attachments"]]
    tables = _settle(platform, catalog, everything | {f"{attached}.t1": "unmanaged"}, place)
    assert tables[f"{attached}.t1"]["decided_by"] == _decided_by(nearer, 1, 1)
    _wait_stopped(temporal, tables[f"{attached}.t1"]["uuid"])

    excluding = [_rule("include", "t*"), _rule("exclude", "t2")]
    assert _save(platform, name, "e2e: excludes t2", excluding)["version"] == 2
    tables = _settle(
        platform, catalog, everything | {f"{attached}.t1": "unmanaged", f"{attached}.t2": "unmanaged"}, place
    )
    assert tables[f"{attached}.t2"]["decided_by"] == _decided_by(policy, 2, 2)
    assert tables[f"{attached}.t3"]["decided_by"] == _decided_by(policy, 2, 1)
    _wait_stopped(temporal, tables[f"{attached}.t2"]["uuid"])

    assert _save(platform, name, "e2e: matches nothing", [_rule("include", "never_*")])["version"] == 3
    nothing = dict.fromkeys(everything, "unmanaged")
    tables = _settle(platform, catalog, nothing, place)
    _wait_stopped(temporal, tables[f"{attached}.t3"]["uuid"])
    assert _save(platform, name, "e2e", [_rule("include", "t*")])["version"] == 4
    _settle(platform, catalog, everything | {f"{attached}.t1": "unmanaged"}, place)

    platform.call("DELETE", f"{POLICIES}/{nearer_name}/attachments/{on_t1}")
    platform.call("DELETE", f"{POLICIES}/{name}/attachments/{attachment}")
    tables = _settle(platform, catalog, nothing, place)
    for table in MANAGED:
        _wait_stopped(temporal, tables[f"{attached}.{table}"]["uuid"])
    wait_until(
        lambda: None if schedule_exists(temporal, schedule) else True,
        timeout=SETTLE_SECONDS,
        interval=3,
        what=f"{schedule} deleted",
    )
    assert catalog not in [found["catalog"] for found in platform.get("/v1/scanned-catalogs")["catalogs"]]


def test_an_exclude_only_policy_on_a_namespace_leaves_its_tables_unmanaged_under_a_catalog_include(
    api: httpx.Client,
    platform: PlatformApi,
    temporal: TemporalSession[Client],
    s3: fs.FileSystem,
    owned_catalog: OwnedCatalog,
    suffix: str,
    cleanup: CleanupStack,
):
    """The catalog includes every table; the namespace's own exclude-only policy is nearer, so its table is left out."""
    catalog = owned_catalog.name
    kept, left_out = OwnedNames.namespace(suffix, "kept"), OwnedNames.namespace(suffix, "left_out")
    _tables(owned_catalog, platform, temporal, s3, cleanup, kept, ("k1",))
    _tables(owned_catalog, platform, temporal, s3, cleanup, left_out, ("l1",))
    place = (kept, left_out)
    everything_name = OwnedNames.discovery_policy(suffix, "include_all")
    everything = _create(platform, api, cleanup, everything_name, [_rule("include", "*")])
    on_catalog = _attach(platform, api, cleanup, everything_name, {"type": "catalog", "path": [catalog]})
    skip_name = OwnedNames.discovery_policy(suffix, "exclude_ns")
    skip = _create(platform, api, cleanup, skip_name, [_rule("exclude", "*")])
    on_namespace = _attach(platform, api, cleanup, skip_name, {"type": "namespace", "path": [catalog, left_out]})

    tables = _settle(platform, catalog, {f"{kept}.k1": "managed", f"{left_out}.l1": "unmanaged"}, place)
    assert tables[f"{kept}.k1"]["decided_by"] == _decided_by(everything, 1, 1)
    assert tables[f"{left_out}.l1"]["decided_by"] == _decided_by(skip, 1, 1)

    platform.call("DELETE", f"{POLICIES}/{skip_name}/attachments/{on_namespace}")
    tables = _settle(platform, catalog, {f"{kept}.k1": "managed", f"{left_out}.l1": "managed"}, place)
    assert tables[f"{left_out}.l1"]["decided_by"] == _decided_by(everything, 1, 1)

    platform.call("DELETE", f"{POLICIES}/{everything_name}/attachments/{on_catalog}")
    tables = _settle(platform, catalog, {f"{kept}.k1": "unmanaged", f"{left_out}.l1": "unmanaged"}, place)
    for table in tables.values():
        _wait_stopped(temporal, table["uuid"])
