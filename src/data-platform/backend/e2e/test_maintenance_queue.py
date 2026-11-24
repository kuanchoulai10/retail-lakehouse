"""Runs wait their turn in the maintenance queue by priority, and a P0 run goes at once in the urgent queue.

A pod-less PodGroup holds the whole normal queue. A P3 manual compaction of ``d`` waits behind it,
and a P0 request for ``d`` moves that waiting job, under the same attempt and name, to the urgent
queue, where it runs while the hold stays. Then ``c`` asks for a P3 compaction and ``b``, set to
P1, for one without a priority; both wait while held. Once the hold is released, ``b`` runs
first and ``c`` only after ``b`` ended, the queue having room for one job.
"""

from __future__ import annotations

from datetime import datetime
from functools import partial
from typing import TYPE_CHECKING

import pyarrow as pa
import pytest
from pyiceberg.partitioning import UNPARTITIONED_PARTITION_SPEC
from pyiceberg.schema import Schema
from pyiceberg.types import LongType, NestedField, StringType

from e2e.support import (
    ManagedTable,
    OwnedNames,
    QueueHolder,
    assert_runs_succeeded,
    job_pod_group,
    wait_until,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from pyarrow import fs
    from pyiceberg.catalog import Catalog
    from temporalio.client import Client

    from e2e.support import CleanupStack, E2eSettings, KubernetesApi, PlatformApi, TemporalSession

pytestmark = pytest.mark.full

RUN_TIMEOUT_SECONDS = 900
SPARK_APPLICATIONS = "/apis/sparkoperator.k8s.io/v1beta2/namespaces/lakehouse-maintenance-operations/sparkapplications"
ACTIVE = ("pending", "queued", "running")
COMPACTION = ["rewrite_data_files"]
SCHEMA = Schema(
    NestedField(1, "id", LongType(), required=False),
    NestedField(2, "note", StringType(), required=False),
)
ROWS = pa.schema([("id", pa.int64()), ("note", pa.string())])


def _manual_runs_only(policy: dict) -> dict:
    policy["dry_run"] = True
    policy["rewrite_data_files"]["options"]["min_input_files"] = 1
    return policy


def _at(text: str) -> datetime:
    return datetime.fromisoformat(text)


def _table(name: str, create: Callable[..., ManagedTable], platform: PlatformApi, iceberg: Catalog, suffix: str) -> str:
    """Create a managed table with two small files and return its uuid."""
    table = create(
        namespace=OwnedNames.namespace(suffix, f"queue_{name}"),
        name=f"tm_e2e_queue_{name}",
        schema=SCHEMA,
        partition_spec=UNPARTITIONED_PARTITION_SPEC,
        policy=(
            OwnedNames.maintenance_policy(suffix, f"queue_{name}"),
            "e2e: manual runs only, for the queue",
            _manual_runs_only,
        ),
        discovery_policy=OwnedNames.discovery_policy(suffix, f"queue_{name}"),
    )
    loaded = table.load(iceberg)
    for n in range(2):
        loaded.append(pa.Table.from_pylist([{"id": n, "note": f"{name}-{n}"}], schema=ROWS))
    return table.wait_until_managed(platform)


def _manual_run(platform: PlatformApi, table_uuid: str, before: set[str]) -> dict:
    runs = [run for run in platform.runs(table_uuid) if run["run_id"] not in before and run["trigger"] == "manual"]
    if not runs:
        raise AssertionError(f"no manual run of {table_uuid} yet")
    [run] = runs
    return run


def _queued(platform: PlatformApi, run_id: str) -> dict:
    """Return the run once its attempt was submitted and waits for its driver."""
    run = platform.get(f"/v1/table-maintenance-runs/{run_id}")
    if run["status"] != "queued" or not run["attempts"] or not run["attempts"][-1]["job_name"]:
        raise AssertionError(f"run {run_id} is {run['status']}: {run['attempts']}")
    return run


def _waiting_group(kubernetes: KubernetesApi, job_name: str) -> dict:
    group = job_pod_group(kubernetes, job_name)
    if group is None:
        raise AssertionError(f"no PodGroup of {job_name} yet")
    return group


def _ended(platform: PlatformApi, run_id: str) -> dict:
    run = platform.get(f"/v1/table-maintenance-runs/{run_id}")
    if run["status"] in ACTIVE:
        raise AssertionError(f"run {run_id} is {run['status']}")
    return run


def _assert_waiting(platform: PlatformApi, kubernetes: KubernetesApi, run_id: str) -> dict:
    """The run, its one attempt and its PodGroup all show it waiting for room in the queue."""
    run = wait_until(lambda: _queued(platform, run_id), timeout=180, interval=2, what=f"{run_id} queued")
    [attempt] = run["attempts"]
    assert (attempt["status"], attempt["started_running_at"]) == ("queued", None), attempt
    group = wait_until(
        lambda: _waiting_group(kubernetes, attempt["job_name"]), timeout=60, interval=2, what="its PodGroup"
    )
    assert group.get("status", {}).get("phase") in ("Pending", "Inqueue"), group.get("status")
    return run


def test_runs_wait_by_priority_and_a_p0_run_goes_at_once(
    platform: PlatformApi,
    iceberg: Catalog,
    s3: fs.S3FileSystem,
    temporal: TemporalSession[Client],
    kubernetes: KubernetesApi,
    settings: E2eSettings,
    suffix: str,
    cleanup: CleanupStack,
):
    """P0 skips the held queue under the same attempt; after the release P1 runs before an earlier P3."""
    wait_until(
        lambda: not kubernetes.list(SPARK_APPLICATIONS)["items"] or None,
        timeout=RUN_TIMEOUT_SECONDS,
        interval=5,
        what="no maintenance Spark job left in the namespace",
    )
    create = partial(
        ManagedTable.create,
        platform=platform,
        iceberg=iceberg,
        s3=s3,
        temporal=temporal,
        cleanup=cleanup,
        catalog=settings.catalog,
    )
    b, c, d = (_table(name, create, platform, iceberg, suffix) for name in "bcd")
    holder = QueueHolder.create(kubernetes, cleanup, OwnedNames.queue_holder(suffix, "queue"))
    wait_until(lambda: holder.phase() == "Inqueue" or None, timeout=60, interval=2, what="the holder admitted")

    before_d = {run["run_id"] for run in platform.runs(d)}
    platform.call("POST", f"/v1/tables/{d}/maintenance", {"operations": COMPACTION, "priority": "P3"})
    d_run = wait_until(lambda: _manual_run(platform, d, before_d), timeout=120, interval=2, what=f"{d}'s run")
    waiting = _assert_waiting(platform, kubernetes, d_run["run_id"])
    [attempt] = waiting["attempts"]
    group = job_pod_group(kubernetes, attempt["job_name"])
    assert group is not None
    assert group.get("status", {}).get("phase") == "Pending", f"d's job is not held: {group.get('status')}"

    platform.call("POST", f"/v1/tables/{d}/maintenance", {"operations": COMPACTION, "priority": "P0"})

    def urgent() -> dict:
        job = kubernetes.get(f"{SPARK_APPLICATIONS}/{attempt['job_name']}")
        options = (job or {}).get("spec", {}).get("batchSchedulerOptions", {})
        if job is None or options.get("queue") != "table-maintenance-urgent":
            raise AssertionError(f"{attempt['job_name']} scheduled with {options}")
        return job

    job = wait_until(urgent, timeout=180, interval=2, what=f"{attempt['job_name']} moved to the urgent queue")
    assert job["spec"]["batchSchedulerOptions"]["priorityClassName"] == "table-maintenance-p0"
    moved = wait_until(
        lambda: _waiting_group(kubernetes, attempt["job_name"]), timeout=60, interval=2, what="the moved PodGroup"
    )
    assert moved["spec"]["queue"] == "table-maintenance-urgent", moved["spec"]
    d_done = wait_until(lambda: _ended(platform, d_run["run_id"]), timeout=RUN_TIMEOUT_SECONDS, interval=5, what="d")
    assert holder.phase() == "Inqueue", "the hold ended before d ran"
    assert_runs_succeeded([d_done])
    assert d_done["priority"] == "P0", d_done["priority"]
    assert [(a["attempt"], a["job_name"]) for a in d_done["attempts"]] == [(1, attempt["job_name"])]
    assert d_done["attempts"][0]["started_running_at"] is not None
    assert [run["run_id"] for run in platform.runs(d) if run["run_id"] not in before_d] == [d_run["run_id"]]

    before_c = {run["run_id"] for run in platform.runs(c)}
    platform.call("POST", f"/v1/tables/{c}/maintenance", {"operations": COMPACTION, "priority": "P3"})
    c_run = wait_until(lambda: _manual_run(platform, c, before_c), timeout=120, interval=2, what=f"{c}'s run")
    _assert_waiting(platform, kubernetes, c_run["run_id"])
    assert platform.call("PUT", f"/v1/tables/{b}/priority", {"priority": "P1"})["priority"] == "P1"
    assert platform.get(f"/v1/tables/{b}")["priority"] == "P1"
    before_b = {run["run_id"] for run in platform.runs(b)}
    platform.call("POST", f"/v1/tables/{b}/maintenance", {"operations": COMPACTION})
    b_run = wait_until(lambda: _manual_run(platform, b, before_b), timeout=120, interval=2, what=f"{b}'s run")
    b_waiting = _assert_waiting(platform, kubernetes, b_run["run_id"])
    b_job = kubernetes.get(f"{SPARK_APPLICATIONS}/{b_waiting['attempts'][0]['job_name']}")
    assert b_job is not None
    options = b_job["spec"]["batchSchedulerOptions"]
    assert (options["queue"], options["priorityClassName"]) == ("table-maintenance", "table-maintenance-p1"), options

    holder.release()
    b_done = wait_until(lambda: _ended(platform, b_run["run_id"]), timeout=RUN_TIMEOUT_SECONDS, interval=5, what="b")
    c_done = wait_until(lambda: _ended(platform, c_run["run_id"]), timeout=RUN_TIMEOUT_SECONDS, interval=5, what="c")
    assert_runs_succeeded([b_done, c_done])
    assert (b_done["priority"], c_done["priority"]) == ("P1", "P3")
    [b_attempt], [c_attempt] = b_done["attempts"], c_done["attempts"]
    assert _at(b_attempt["started_running_at"]) < _at(c_attempt["started_running_at"]), (b_attempt, c_attempt)
    assert _at(c_attempt["started_running_at"]) >= _at(b_attempt["finished_at"]), (b_attempt, c_attempt)
