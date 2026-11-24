"""Each reconciliation records why it ran and which policy, version and target it ran under.

One dry-run table in a catalog of the module's own: its maintenance policy sits on its namespace,
so a policy attached on the table is the nearer one. Dry run keeps every check free of runs.
Marked ``full``: it waits for discovery and for reconciliations.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

import pyarrow as pa
import pytest

from e2e.support import OwnedNames, assert_prefixed_ids, drop_table, wait_until, wait_until_unmanaged

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx
    from pyarrow import fs
    from temporalio.client import Client

    from e2e.support import CleanupStack, OwnedCatalog, PlatformApi, TemporalSession

pytestmark = pytest.mark.full

MAINTENANCE = "/v1/maintenance-policies"
DISCOVERY = "/v1/discovery-policies"
ROWS = pa.schema([pa.field("id", pa.int64())])
RECORD_SECONDS = 180
QUIET_SECONDS = 20
MANAGE = {"outcome": "manage", "conditions": [{"attribute": "table_name", "operator": "glob", "values": ["t*"]}]}


def _delete_if_present(api: httpx.Client, path: str) -> None:
    reply = api.delete(path)
    assert reply.status_code in (204, 404), f"DELETE {path} answered {reply.status_code}: {reply.text}"


def _records(platform: PlatformApi, table_uuid: str) -> list[dict]:
    return platform.get(f"/v1/tables/{table_uuid}/reconciliations", limit=200)


def _record(platform: PlatformApi, table_uuid: str, what: str, matches: Callable[[dict], bool]) -> dict:
    def found() -> dict:
        records = _records(platform, table_uuid)
        hits = [record for record in records if matches(record)]
        if not hits:
            raise AssertionError([(r["wake_reasons"], r["policy_name"], r["policy_version"]) for r in records[:5]])
        return hits[0]

    return wait_until(found, timeout=RECORD_SECONDS, interval=3, what=what)


def _save(platform: PlatformApi, name: str, content: dict[str, Any]) -> dict:
    version = platform.get(f"{MAINTENANCE}/{name}")["version"]
    return platform.call("PUT", f"{MAINTENANCE}/{name}", {"version": version, **content})


def test_a_reconciliation_records_why_it_ran_and_under_which_policy(
    api: httpx.Client,
    platform: PlatformApi,
    temporal: TemporalSession[Client],
    s3: fs.FileSystem,
    owned_catalog: OwnedCatalog,
    suffix: str,
    cleanup: CleanupStack,
):
    """Becoming managed, attaching a nearer policy and each save are recorded; a discovery scan is not."""
    catalog, namespace = owned_catalog.name, OwnedNames.namespace(suffix, "records")
    owned_catalog.iceberg.create_namespace((namespace,))
    cleanup.push(f"drop {namespace}", lambda: owned_catalog.iceberg.drop_namespace((namespace,)))
    owned_catalog.iceberg.create_table((namespace, "t"), ROWS)
    cleanup.push(f"drop {namespace}.t", lambda: drop_table(owned_catalog.iceberg, s3, (namespace, "t")))

    on_namespace = OwnedNames.maintenance_policy(suffix, "records")
    platform.create_maintenance_policy(on_namespace, "e2e", lambda body: {**body, "dry_run": True})
    cleanup.push(f"delete {on_namespace}", lambda: _delete_if_present(api, f"{MAINTENANCE}/{on_namespace}"))
    namespace_attachment = platform.attach(
        "maintenance-policies", on_namespace, {"type": "namespace", "path": [catalog, namespace]}
    )
    cleanup.push(
        f"detach {on_namespace}",
        lambda: _delete_if_present(api, f"{MAINTENANCE}/{on_namespace}/attachments/{namespace_attachment}"),
    )
    cleanup.push(
        f"wait until {namespace}.t is unmanaged",
        lambda: wait_until_unmanaged(platform, temporal, (catalog, namespace, "t")),
    )
    discovery = OwnedNames.discovery_policy(suffix, "records")
    platform.call(
        "POST", DISCOVERY, {"name": discovery, "description": "e2e", "no_match_outcome": "unmanage", "rules": [MANAGE]}
    )
    cleanup.push(f"delete {discovery}", lambda: _delete_if_present(api, f"{DISCOVERY}/{discovery}"))
    discovery_attachment = platform.attach(
        "discovery-policies", discovery, {"type": "namespace", "path": [catalog, namespace]}
    )
    cleanup.push(
        f"detach {discovery}",
        lambda: _delete_if_present(api, f"{DISCOVERY}/{discovery}/attachments/{discovery_attachment}"),
    )

    def managed_uuid() -> str | None:
        found = platform.table(catalog, namespace, "t")
        return found["uuid"] if found and found["status"] == "managed" else None

    table_uuid = wait_until(managed_uuid, timeout=RECORD_SECONDS, interval=3, what=f"{namespace}.t managed")
    managed = _record(
        platform, table_uuid, "a table_managed record", lambda r: r["wake_reasons"] == {"table_managed": 1}
    )
    assert (managed["policy_name"], managed["dry_run"]) == (on_namespace, True)
    assert managed["policy_target"] == {"type": "namespace", "path": [catalog, namespace]}
    assert_prefixed_ids({"rc": [managed["reconciliation_id"]]})

    count = len(_records(platform, table_uuid))
    version = platform.get(f"{DISCOVERY}/{discovery}")["version"]
    rescan = {"version": version, "description": "e2e, rescanned", "no_match_outcome": "unmanage", "rules": [MANAGE]}
    platform.call("PUT", f"{DISCOVERY}/{discovery}", rescan)
    time.sleep(QUIET_SECONDS)
    assert len(_records(platform, table_uuid)) == count, _records(platform, table_uuid)[:3]

    nearer = OwnedNames.maintenance_policy(suffix, "nearer")
    first = platform.create_maintenance_policy(
        nearer,
        "e2e: nearer",
        lambda body: {
            **body,
            "dry_run": True,
            "on": {"schedule": {"every_seconds": 300}, "catalog_commit": {"debounce_seconds": 120}},
            "rewrite_manifests": None,
            "expire_snapshots": None,
            "remove_orphan_files": None,
        },
    )
    cleanup.push(f"delete {nearer}", lambda: _delete_if_present(api, f"{MAINTENANCE}/{nearer}"))
    table_attachment = platform.attach(
        "maintenance-policies", nearer, {"type": "table", "path": [catalog, namespace, "t"]}
    )
    cleanup.push(
        f"detach {nearer}", lambda: _delete_if_present(api, f"{MAINTENANCE}/{nearer}/attachments/{table_attachment}")
    )

    def changed_to(version: int) -> Callable[[dict], bool]:
        return lambda r: (
            "policy_changed" in r["wake_reasons"] and (r["policy_name"], r["policy_version"]) == (nearer, version)
        )

    attached = _record(platform, table_uuid, f"a policy_changed record of {nearer} v1", changed_to(1))
    assert (attached["policy_id"], attached["policy_deleted"], attached["dry_run"]) == (first["id"], False, True)
    assert attached["policy_target"] == {"type": "table", "path": [catalog, namespace, "t"]}
    assert_prefixed_ids({"mp": [attached["policy_id"]]})

    content = {
        key: first[key]
        for key in (
            "description",
            "dry_run",
            "rewrite_data_files",
            "rewrite_manifests",
            "expire_snapshots",
            "remove_orphan_files",
        )
    }
    assert _save(platform, nearer, {**content, "on": {"schedule": {"every_seconds": 600}}})["version"] == 2
    _record(platform, table_uuid, f"a policy_changed record of {nearer} v2", changed_to(2))
    original = platform.get(f"{MAINTENANCE}/{nearer}/versions/1")
    assert (original["version"], original["on"], original["rewrite_data_files"]) == (
        1,
        first["on"],
        first["rewrite_data_files"],
    )
    missing = api.get(f"{MAINTENANCE}/{nearer}/versions/99")
    assert missing.status_code == 404, missing.text

    expiry_only = {
        **content,
        "on": {"schedule": {"every_seconds": 600}},
        "rewrite_data_files": None,
        "expire_snapshots": {"target": {"min_snapshots_to_keep": 10, "max_snapshot_age_seconds": 86400}},
    }
    assert _save(platform, nearer, expiry_only)["version"] == 3
    latest = _record(platform, table_uuid, f"a policy_changed record of {nearer} v3", changed_to(3))
    [compaction] = [operation for operation in latest["operations"] if operation["operation"] == "rewrite_data_files"]
    assert (compaction["result"], compaction["run_id"]) == ("off", None)
    assert [run for run in platform.runs(table_uuid) if run["operation"] == "rewrite_data_files"] == []
