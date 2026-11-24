"""Stopping a table's maintenance midway fails the run in flight and skips the runs it never reached.

A dry-run policy keeps the platform from maintaining the table on its own; a manual request plans
a compaction, a manifest rewrite and an expiry. Once the compaction's job was submitted, its
maintenance execution is cancelled through Temporal: the compaction ends failed by the cancel, the
two later runs are skipped with the reason, no run stays pending, no Spark job of these runs is
left, and the table's reconciliation keeps running.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pyarrow as pa
import pytest
from pyiceberg.partitioning import UNPARTITIONED_PARTITION_SPEC
from pyiceberg.schema import Schema
from pyiceberg.types import LongType, NestedField, StringType

from e2e.support import ManagedTable, OwnedNames, reconciliation_running, wait_until

if TYPE_CHECKING:
    from pyarrow import fs
    from pyiceberg.catalog import Catalog
    from temporalio.client import Client

    from e2e.support import CleanupStack, E2eSettings, KubernetesApi, PlatformApi, TemporalSession

pytestmark = pytest.mark.full

PLAN = ("rewrite_data_files", "rewrite_manifests", "expire_snapshots")
NOT_REACHED = "the table's maintenance stopped before this run started"
SPARK_APPLICATIONS = "/apis/sparkoperator.k8s.io/v1beta2/namespaces/lakehouse-maintenance-operations/sparkapplications"
RUN_ID = "table-maintenance/run-id"
ACTIVE = ("pending", "queued", "running")
SCHEMA = Schema(
    NestedField(1, "id", LongType(), required=False),
    NestedField(2, "note", StringType(), required=False),
)
ROWS = pa.schema([("id", pa.int64()), ("note", pa.string())])


def _manual_runs_only(policy: dict) -> dict:
    policy["dry_run"] = True
    policy["rewrite_data_files"]["options"]["min_input_files"] = 1
    return policy


def _plan(platform: PlatformApi, table_uuid: str, before: set[str]) -> list[dict]:
    runs = [run for run in platform.runs(table_uuid) if run["run_id"] not in before and run["trigger"] == "manual"]
    if len(runs) < len(PLAN):
        raise AssertionError(f"manual runs so far: {[(run['operation'], run['status']) for run in runs]}")
    return sorted(runs, key=lambda run: PLAN.index(run["operation"]))


def _submitted(platform: PlatformApi, run_id: str) -> dict:
    run = platform.get(f"/v1/table-maintenance-runs/{run_id}")
    if run["status"] not in ("queued", "running") or not run["attempts"] or not run["attempts"][-1]["job_name"]:
        raise AssertionError(f"run {run_id} is {run['status']}: {run['attempts']}")
    return run


def _settled(platform: PlatformApi, table_uuid: str, run_ids: list[str]) -> list[dict]:
    runs = [platform.get(f"/v1/table-maintenance-runs/{run_id}") for run_id in run_ids]
    if any(run["status"] in ACTIVE for run in runs):
        raise AssertionError(f"runs not ended: {[(run['operation'], run['status']) for run in runs]}")
    return runs


def test_a_cancel_fails_the_run_in_flight_and_skips_the_rest(
    platform: PlatformApi,
    iceberg: Catalog,
    s3: fs.S3FileSystem,
    temporal: TemporalSession[Client],
    kubernetes: KubernetesApi,
    settings: E2eSettings,
    suffix: str,
    cleanup: CleanupStack,
):
    """The compaction fails as cancelled, the manifest rewrite and expiry are skipped, nothing is left behind."""
    stopped = ManagedTable.create(
        platform=platform,
        iceberg=iceberg,
        s3=s3,
        temporal=temporal,
        cleanup=cleanup,
        catalog=settings.catalog,
        namespace=OwnedNames.namespace(suffix, "cancel"),
        name="tm_e2e_cancel",
        schema=SCHEMA,
        partition_spec=UNPARTITIONED_PARTITION_SPEC,
        policy=(OwnedNames.maintenance_policy(suffix, "cancel"), "e2e: manual runs only, cancelled", _manual_runs_only),
        discovery_policy=OwnedNames.discovery_policy(suffix, "cancel"),
    )
    table = stopped.load(iceberg)
    for n in range(2):
        table.append(pa.Table.from_pylist([{"id": n, "note": f"cancel-{n}"}], schema=ROWS))
    uuid = stopped.wait_until_managed(platform)
    before = {run["run_id"] for run in platform.runs(uuid)}

    platform.call("POST", f"/v1/tables/{uuid}/maintenance", {"operations": list(PLAN)})
    runs = wait_until(lambda: _plan(platform, uuid, before), timeout=120, interval=2, what=f"the plan of {uuid}")
    wait_until(
        lambda: _submitted(platform, runs[0]["run_id"]), timeout=180, interval=1, what="the compaction submitted"
    )

    async def cancel(client: Client) -> None:
        await client.get_workflow_handle(f"table-maintenance:table-uuid={uuid}").cancel()

    temporal.run(cancel)
    run_ids = [run["run_id"] for run in runs]
    compaction, manifests, expiry = wait_until(
        lambda: _settled(platform, uuid, run_ids), timeout=300, interval=3, what=f"the cancelled plan of {uuid}"
    )
    assert compaction["status"] == "failed", compaction
    last = compaction["attempts"][-1]
    assert (last["failure_class"], last["next_step"]) == ("cancelled", "cancelled"), last
    assert last["finished_at"] is not None, last
    for skipped in (manifests, expiry):
        assert (skipped["status"], skipped["skip_reason"]) == ("skipped", NOT_REACHED), skipped
        assert skipped["attempts"] == [], skipped
    assert not [run for run in platform.runs(uuid) if run["status"] == "pending"]

    def no_jobs_left() -> bool | None:
        selector = f"{RUN_ID} in ({','.join(run_ids)})"
        return not kubernetes.list(SPARK_APPLICATIONS, label_selector=selector)["items"] or None

    wait_until(no_jobs_left, timeout=120, interval=3, what="no Spark job of the cancelled runs")
    assert reconciliation_running(temporal, uuid)
