"""Discovery manages what the nearest attachment says, and stops what it no longer says.

One lifecycle in a catalog of the module's own: attaching a managing policy schedules and scans the
catalog, a table-level attachment of the default unmanages one table, a save that matches nothing
unmanages the rest, and detaching retires the schedule. Marked ``full``: each step waits for scans
and reconciliations.
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


def _rule(glob: str) -> dict:
    return {"outcome": "manage", "conditions": [{"attribute": "table_name", "operator": "glob", "values": [glob]}]}


def _delete_if_present(api: httpx.Client, path: str) -> None:
    reply = api.delete(path)
    assert reply.status_code in (204, 404), f"DELETE {path} answered {reply.status_code}: {reply.text}"


def _settle(platform: PlatformApi, catalog: str, statuses: dict[str, str]) -> dict[str, dict]:
    """Wait until the catalog's tables (``namespace.table``) have exactly these statuses, and return them."""

    def settled() -> dict[str, dict]:
        tables = {f"{t['namespace']}.{t['table']}": t for t in platform.get("/v1/tables") if t["catalog"] == catalog}
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

    wait_until(stopped, timeout=SETTLE_SECONDS, interval=3, what=f"{workflow} stopped")


def _save(platform: PlatformApi, name: str, description: str, glob: str) -> dict:
    version = platform.get(f"{POLICIES}/{name}")["version"]
    body = {"version": version, "description": description, "no_match_outcome": "unmanage", "rules": [_rule(glob)]}
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
    """Attach, attach the default nearer, save a rule that matches nothing, restore it, detach."""
    catalog = owned_catalog.name
    attached, other = OwnedNames.namespace(suffix, "attached"), OwnedNames.namespace(suffix, "other")
    for namespace, tables in ((attached, MANAGED), (other, ("x",))):
        owned_catalog.iceberg.create_namespace((namespace,))
        cleanup.push(
            f"drop {namespace}", lambda namespace=namespace: owned_catalog.iceberg.drop_namespace((namespace,))
        )
        for table in tables:
            place = (namespace, table)
            owned_catalog.iceberg.create_table(place, ROWS)
            cleanup.push(f"drop {namespace}.{table}", lambda place=place: drop_table(owned_catalog.iceberg, s3, place))
            cleanup.push(
                f"wait until {namespace}.{table} is unmanaged",
                lambda place=place: wait_until_unmanaged(platform, temporal, (catalog, place[0], place[1])),
            )
    default = platform.get(f"{POLICIES}/default")
    name = OwnedNames.discovery_policy(suffix, "lifecycle")
    policy = platform.call(
        "POST", POLICIES, {"name": name, "description": "e2e", "no_match_outcome": "unmanage", "rules": [_rule("t*")]}
    )
    cleanup.push(f"delete {name}", lambda: _delete_if_present(api, f"{POLICIES}/{name}"))
    [rule] = policy["rules"]
    attachment = platform.attach("discovery-policies", name, {"type": "namespace", "path": [catalog, attached]})
    cleanup.push(f"detach {name}", lambda: _delete_if_present(api, f"{POLICIES}/{name}/attachments/{attachment}"))

    everything = {f"{attached}.{table}": "managed" for table in MANAGED} | {f"{other}.x": "unmanaged"}
    tables = _settle(platform, catalog, everything)
    for table in MANAGED:
        found = tables[f"{attached}.{table}"]
        assert (found["matched_policy_id"], found["matched_policy_version"], found["matched_rule_id"]) == (
            policy["id"],
            1,
            rule["id"],
        )
    unattached = tables[f"{other}.x"]
    assert (unattached["matched_policy_id"], unattached["matched_rule_id"]) == (default["id"], None)
    schedule = f"table-discovery:catalog={catalog}"
    assert schedule_exists(temporal, schedule)

    async def interval(client: Client) -> timedelta:
        described = await client.get_schedule_handle(schedule).describe()
        [every] = described.schedule.spec.intervals
        return every.every

    assert temporal.run(interval) == timedelta(seconds=platform.platform_setting("discovery_interval_seconds"))
    scanned = {found["catalog"]: found for found in platform.get("/v1/scanned-catalogs")["catalogs"]}
    assert scanned[catalog]["failure"] is None and scanned[catalog]["last_discovered_at"], scanned.get(catalog)

    nearest = platform.attach("discovery-policies", "default", {"type": "table", "path": [catalog, attached, "t1"]})
    cleanup.push("detach default from t1", lambda: _delete_if_present(api, f"{POLICIES}/default/attachments/{nearest}"))
    assert nearest in [found["id"] for found in platform.get(f"{POLICIES}/default/attachments")["attachments"]]
    tables = _settle(platform, catalog, everything | {f"{attached}.t1": "unmanaged"})
    assert tables[f"{attached}.t1"]["matched_policy_id"] == default["id"]
    _wait_stopped(temporal, tables[f"{attached}.t1"]["uuid"])

    assert _save(platform, name, "e2e: matches nothing", "never_*")["version"] == 2
    nothing = dict.fromkeys(everything, "unmanaged")
    tables = _settle(platform, catalog, nothing)
    for table in ("t2", "t3"):
        _wait_stopped(temporal, tables[f"{attached}.{table}"]["uuid"])
    assert _save(platform, name, "e2e", "t*")["version"] == 3
    _settle(platform, catalog, everything | {f"{attached}.t1": "unmanaged"})

    platform.call("DELETE", f"{POLICIES}/default/attachments/{nearest}")
    platform.call("DELETE", f"{POLICIES}/{name}/attachments/{attachment}")
    tables = _settle(platform, catalog, nothing)
    for table in MANAGED:
        _wait_stopped(temporal, tables[f"{attached}.{table}"]["uuid"])
    wait_until(
        lambda: None if schedule_exists(temporal, schedule) else True,
        timeout=SETTLE_SECONDS,
        interval=3,
        what=f"{schedule} deleted",
    )
    assert catalog not in [found["catalog"] for found in platform.get("/v1/scanned-catalogs")["catalogs"]]
