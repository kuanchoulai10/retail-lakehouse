"""A scheduled compaction rewrites only the partitions over the policy's target, one named with a quote.

The table is partitioned by ``region``; four appends leave four files in each of ``north`` and
``o'neil``. A policy that allows one reducible file per partition, checked every 300 s and 90 s
after the first commit not yet checked, has the platform compact both partitions on the check the
commits' window closes: the window outlasts the quiet period, so the check does not wait for the
schedule.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pyarrow as pa
import pytest
from pyiceberg.partitioning import PartitionField, PartitionSpec
from pyiceberg.schema import Schema
from pyiceberg.transforms import IdentityTransform
from pyiceberg.types import LongType, NestedField, StringType

from e2e.support import (
    ManagedTable,
    OwnedNames,
    assert_attempts_timed,
    assert_prefixed_ids,
    assert_runs_succeeded,
    reconciliation_running,
    wait_until,
)

if TYPE_CHECKING:
    from pyarrow import fs
    from pyiceberg.catalog import Catalog
    from temporalio.client import Client

    from e2e.support import CleanupStack, E2eSettings, PlatformApi, TemporalSession

pytestmark = pytest.mark.full

SCHEDULE_SECONDS = 300
COMMIT_WINDOW_SECONDS = 90
SCHEDULE_TIMEOUT_SECONDS = 120
RUN_TIMEOUT_SECONDS = 3600
ACTIVE = ("pending", "queued", "running", "retry_waiting")

SCHEMA = Schema(
    NestedField(1, "id", LongType(), required=False),
    NestedField(2, "region", StringType(), required=False),
    NestedField(3, "note", StringType(), required=False),
)
SPEC = PartitionSpec(PartitionField(source_id=2, field_id=1000, transform=IdentityTransform(), name="region"))
ROWS = pa.schema([("id", pa.int64()), ("region", pa.string()), ("note", pa.string())])


def _per_partition_compaction(policy: dict) -> dict:
    for operation in ("rewrite_manifests", "expire_snapshots", "remove_orphan_files"):
        policy.pop(operation, None)
    policy["on"] = {
        "schedule": {"every_seconds": SCHEDULE_SECONDS},
        "catalog_commit": {"debounce_seconds": COMMIT_WINDOW_SECONDS},
    }
    policy["rewrite_data_files"]["target"]["reducible_files"]["at_most"] = 1
    return policy


def _settled_scheduled_compaction(platform: PlatformApi, table_uuid: str) -> list[dict]:
    runs = platform.runs(table_uuid)
    ended = [
        run
        for run in runs
        if run["trigger"] == "scheduled" and run["operation"] == "rewrite_data_files" and run["status"] not in ACTIVE
    ]
    active = [run["run_id"] for run in runs if run["status"] in ACTIVE]
    if not ended or active:
        summary = [(run["trigger"], run["operation"], run["status"]) for run in runs]
        raise AssertionError(f"no ended scheduled compaction with nothing in flight yet: {summary}")
    return runs


def test_a_scheduled_compaction_rewrites_the_partitions_over_the_target(
    platform: PlatformApi,
    iceberg: Catalog,
    s3: fs.S3FileSystem,
    temporal: TemporalSession[Client],
    settings: E2eSettings,
    suffix: str,
    cleanup: CleanupStack,
):
    """Both partitions over the target are compacted by a scheduled run, and the table ends with fewer files."""
    regions = ManagedTable.create(
        platform=platform,
        iceberg=iceberg,
        s3=s3,
        temporal=temporal,
        cleanup=cleanup,
        catalog=settings.catalog,
        namespace=OwnedNames.namespace(suffix, "regions"),
        name="tm_e2e_regions",
        schema=SCHEMA,
        partition_spec=SPEC,
        policy=(
            OwnedNames.maintenance_policy(suffix, "regions"),
            "e2e: scheduled per-partition compaction",
            _per_partition_compaction,
        ),
        discovery_policy=OwnedNames.discovery_policy(suffix, "regions"),
    )

    async def discovery_schedule(client: Client) -> bool:
        await client.get_schedule_handle(f"table-discovery:catalog={settings.catalog}").describe()
        return True

    wait_until(
        lambda: temporal.run(discovery_schedule),
        timeout=SCHEDULE_TIMEOUT_SECONDS,
        interval=5,
        what=f"the discovery schedule of {settings.catalog}",
    )
    scanned = platform.get("/v1/scanned-catalogs")["catalogs"]
    assert any(c["catalog"] == settings.catalog and c["failure"] is None for c in scanned), scanned

    table = regions.load(iceberg)
    for n in (1, 3, 5, 7):
        rows = [(n, "north", f"note-{n}"), (n + 1, "o'neil", f"note-{n + 1}")]
        table.append(pa.Table.from_pylist([dict(zip(ROWS.names, row, strict=True)) for row in rows], schema=ROWS))
    files_before = regions.file_count(iceberg)
    uuid = regions.wait_until_managed(platform)

    runs = wait_until(
        lambda: _settled_scheduled_compaction(platform, uuid),
        timeout=RUN_TIMEOUT_SECONDS,
        interval=15,
        what=f"a scheduled compaction of {regions.namespace}.{regions.name}",
    )
    assert_runs_succeeded(runs)
    assert_attempts_timed(runs)
    compacted: list[str | None] = []
    for run in runs:
        if run["operation"] != "rewrite_data_files":
            continue
        specs = platform.get(f"/v1/table-maintenance-runs/{run['run_id']}")["partitions"]
        assert specs, f"run {run['run_id']} compacted the whole table, not the partitions over the target"
        assert all(spec["spec_id"] == 0 and spec["partitions"] for spec in specs), specs
        compacted.extend(value for spec in specs for partition in spec["partitions"] for value in partition)
    assert "o'neil" in compacted, f"no run compacted the partition o'neil, whose value holds a quote: {compacted}"

    effective = platform.get(f"/v1/tables/{uuid}/effective-policies")["policies"]
    assert [entry["kind"] for entry in effective] == ["maintenance", "discovery"]
    maintenance, discovery = effective
    assert maintenance["policy_name"] == regions.maintenance_policy
    assert maintenance["attachment_id"] == regions.maintenance_attachment_id
    assert maintenance["target"] == {
        "type": "table",
        "path": [settings.catalog, regions.namespace, regions.name],
        "table_uuid": uuid,
    }
    assert_prefixed_ids({"pa": [regions.maintenance_attachment_id], "da": [regions.discovery_attachment_id]})
    assert discovery["policy_name"] == regions.discovery_policy["name"]
    assert discovery["attachment_id"] == regions.discovery_attachment_id
    assert discovery["target"] == {
        "type": "namespace",
        "path": [settings.catalog, regions.namespace],
        "table_uuid": None,
    }

    files_after = regions.file_count(iceberg)
    assert files_after < files_before, f"files {files_before} -> {files_after}"
    assert platform.get(f"/v1/tables/{uuid}/metrics/current")["metrics"]["data_files"] is not None
    assert reconciliation_running(temporal, uuid)
