"""A table is checked on its schedule and after a window of catalog commits, and a dry run starts nothing.

A dry-run policy checks the table every 60 s and 30 s after the first commit not yet checked. A
check on the schedule is recorded within an interval. With the schedule moved to an hour (a policy
change sets the next scheduled check one new interval after the check it asks for), a
burst of ten appends opens one window: one record counts the ten commits, about 30 s after the
first, and finds a compaction it would start but does not. With the commit window removed from the
policy, three appends wait for the schedule.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pyarrow as pa
import pytest
from pyiceberg.partitioning import UNPARTITIONED_PARTITION_SPEC
from pyiceberg.schema import Schema
from pyiceberg.types import LongType, NestedField, StringType

from e2e.support import ManagedTable, OwnedNames, wait_until

if TYPE_CHECKING:
    from collections.abc import Callable

    from pyarrow import fs
    from pyiceberg.catalog import Catalog
    from temporalio.client import Client

    from e2e.support import CleanupStack, E2eSettings, PlatformApi, TemporalSession

pytestmark = pytest.mark.full

SCHEDULE_SECONDS = 60
COMMIT_WINDOW_SECONDS = 30
EVENT_LATENCY_SECONDS = 30
NOT_SENT = ("id", "name", "is_default", "created_at", "updated_at")
SCHEMA = Schema(
    NestedField(1, "id", LongType(), required=False),
    NestedField(2, "note", StringType(), required=False),
)
ROWS = pa.schema([("id", pa.int64()), ("note", pa.string())])


def _checked_on_schedule_and_commits(policy: dict) -> dict:
    for operation in ("rewrite_manifests", "expire_snapshots", "remove_orphan_files"):
        policy.pop(operation, None)
    policy["dry_run"] = True
    policy["on"] = {
        "schedule": {"every_seconds": SCHEDULE_SECONDS},
        "catalog_commit": {"debounce_seconds": COMMIT_WINDOW_SECONDS},
    }
    policy["rewrite_data_files"]["target"] = {"reducible_files": {"at_most": 1}, "per": "table"}
    return policy


def _at(text: str) -> datetime:
    return datetime.fromisoformat(text)


def _records(platform: PlatformApi, table_uuid: str) -> list[dict]:
    return platform.get(f"/v1/tables/{table_uuid}/reconciliations")


def _new_record(platform: PlatformApi, table_uuid: str, known: set[str], wanted: Callable[[dict], bool]) -> dict:
    found = [r for r in _records(platform, table_uuid) if r["reconciliation_id"] not in known and wanted(r)]
    if not found:
        raise AssertionError(f"no new record of {table_uuid} as wanted")
    return found[0]


def _update(platform: PlatformApi, name: str, on: dict) -> None:
    """Replace the policy's triggers and keep the rest of its content; the change asks for a check."""
    current = platform.get(f"/v1/maintenance-policies/{name}")
    body = {key: value for key, value in current.items() if key not in NOT_SENT} | {"on": on}
    platform.call("PUT", f"/v1/maintenance-policies/{name}", body)


def _known(platform: PlatformApi, table_uuid: str) -> set[str]:
    return {record["reconciliation_id"] for record in _records(platform, table_uuid)}


def _after_policy_change(platform: PlatformApi, table_uuid: str, known: set[str]) -> set[str]:
    """Wait for the check the policy change asks for, and return every record id known then."""
    wait_until(
        lambda: _new_record(platform, table_uuid, known, lambda r: r["wake_reasons"].get("policy_changed", 0) >= 1),
        timeout=120,
        interval=2,
        what=f"the policy-changed check of {table_uuid}",
    )
    return _known(platform, table_uuid)


def test_checks_follow_the_schedule_and_the_commit_window(
    platform: PlatformApi,
    iceberg: Catalog,
    s3: fs.S3FileSystem,
    temporal: TemporalSession[Client],
    settings: E2eSettings,
    suffix: str,
    cleanup: CleanupStack,
):
    """A schedule record, one commit record counting ten commits that starts nothing, then commits that wait."""
    policy = OwnedNames.maintenance_policy(suffix, "triggers")
    watched = ManagedTable.create(
        platform=platform,
        iceberg=iceberg,
        s3=s3,
        temporal=temporal,
        cleanup=cleanup,
        catalog=settings.catalog,
        namespace=OwnedNames.namespace(suffix, "triggers"),
        name="tm_e2e_triggers",
        schema=SCHEMA,
        partition_spec=UNPARTITIONED_PARTITION_SPEC,
        policy=(policy, "e2e: dry run checked on schedule and commits", _checked_on_schedule_and_commits),
        discovery_policy=OwnedNames.discovery_policy(suffix, "triggers"),
    )
    uuid = watched.wait_until_managed(platform)
    known = _known(platform, uuid)
    scheduled = wait_until(
        lambda: _new_record(platform, uuid, known, lambda r: r["wake_reasons"].get("schedule", 0) >= 1),
        timeout=SCHEDULE_SECONDS * 2.5,
        interval=5,
        what=f"a scheduled check of {uuid}",
    )
    assert "catalog_commit" not in scheduled["wake_reasons"], scheduled

    window = {"debounce_seconds": COMMIT_WINDOW_SECONDS}
    _update(platform, policy, {"schedule": {"every_seconds": 3600}, "catalog_commit": window})
    known = _after_policy_change(platform, uuid, _known(platform, uuid))
    table = watched.load(iceberg)
    for n in range(10):
        table.append(pa.Table.from_pylist([{"id": n, "note": f"burst-{n}"}], schema=ROWS))
    snapshots = sorted(watched.load(iceberg).snapshots(), key=lambda snapshot: snapshot.sequence_number)
    first_commit = datetime.fromtimestamp(snapshots[-10].timestamp_ms / 1000, UTC)
    committed = wait_until(
        lambda: _new_record(platform, uuid, known, lambda r: "catalog_commit" in r["wake_reasons"]),
        timeout=COMMIT_WINDOW_SECONDS + EVENT_LATENCY_SECONDS + 60,
        interval=2,
        what=f"the commit-window check of {uuid}",
    )
    opened = first_commit + timedelta(seconds=COMMIT_WINDOW_SECONDS)
    assert opened <= _at(committed["reconciled_at"]) <= opened + timedelta(seconds=EVENT_LATENCY_SECONDS), committed
    assert committed["wake_reasons"]["catalog_commit"] == 10, committed["wake_reasons"]
    assert committed["dry_run"] is True
    [compaction] = [o for o in committed["operations"] if o["operation"] == "rewrite_data_files"]
    assert (compaction["result"], compaction["run_id"]) == ("would_start", None), compaction
    wait_until(
        lambda: datetime.now(UTC) > opened + timedelta(seconds=COMMIT_WINDOW_SECONDS) or None,
        timeout=COMMIT_WINDOW_SECONDS * 3,
        interval=2,
        what="a second window's end, had one opened",
    )
    windows = [
        r
        for r in _records(platform, uuid)
        if r["reconciliation_id"] not in known and "catalog_commit" in r["wake_reasons"]
    ]
    assert windows == [committed], [r["wake_reasons"] for r in windows]
    assert platform.runs(uuid) == []

    _update(platform, policy, {"schedule": {"every_seconds": SCHEDULE_SECONDS}})
    known = _after_policy_change(platform, uuid, _known(platform, uuid))
    for n in range(3):
        table = watched.load(iceberg)
        table.append(pa.Table.from_pylist([{"id": 100 + n, "note": f"late-{n}"}], schema=ROWS))
    later = wait_until(
        lambda: _new_record(platform, uuid, known, lambda r: True),
        timeout=SCHEDULE_SECONDS * 2.5,
        interval=5,
        what=f"the next check of {uuid}",
    )
    assert later["wake_reasons"].get("schedule", 0) >= 1, later["wake_reasons"]
    assert "catalog_commit" not in later["wake_reasons"], later["wake_reasons"]
