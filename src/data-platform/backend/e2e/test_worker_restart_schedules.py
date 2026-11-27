"""A worker that starts rebuilds the one discovery schedule, and the schedule scans each catalog.

The schedule ``table-discovery`` is the cluster's own, shared by every catalog. The scenario deletes it
behind the platform's back, restarts the worker Deployment (the only object the e2e's Role lets it
change) and waits for the schedule to come back, as configured and not paused. Triggering it then
starts a new round (``table-discovery:round-<time>``), which completes and starts a scan of a catalog of
the module's own (it holds a discovery policy) as its child; that scan completes.
This is the only scenario that deletes the schedule; whatever happens, its undo leaves it recreated.
Marked ``full``: a restart takes minutes.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

import pytest
from temporalio.client import ScheduleActionStartWorkflow, ScheduleOverlapPolicy, WorkflowExecutionStatus

from e2e.support import (
    KubernetesApi,
    OwnedNames,
    latest_run,
    schedule_exists,
    scheduled_workflows,
    trigger_schedule,
    wait_until,
)

if TYPE_CHECKING:
    import httpx
    from temporalio.client import Client, ScheduleDescription

    from e2e.support import CleanupStack, OwnedCatalog, PlatformApi, TemporalSession, WorkflowRun

pytestmark = pytest.mark.full

POLICIES = "/v1/discovery-policies"
NAMESPACE = "lakehouse-control-plane"
WORKER = "table-maintenance-worker"
SCHEDULE = "table-discovery"
ROUND = "table-discovery:round"
NEVER = {"action": "include", "table_name_pattern": "never_*"}
RESTART_SECONDS = 240
SCAN_SECONDS = 180


def _delete_if_present(api: httpx.Client, path: str) -> None:
    reply = api.delete(path)
    assert reply.status_code in (204, 404), f"DELETE {path} answered {reply.status_code}: {reply.text}"


def _rolled_out(kubernetes: KubernetesApi, stamp: str) -> dict:
    """Return the worker Deployment once every replica runs the restarted template and is available."""
    deployment = kubernetes.deployment(NAMESPACE, WORKER)
    annotations = deployment["spec"]["template"]["metadata"].get("annotations", {})
    status, wanted = deployment["status"], deployment["spec"]["replicas"]
    done = (
        annotations.get("kubectl.kubernetes.io/restartedAt") == stamp
        and status.get("observedGeneration", 0) >= deployment["metadata"]["generation"]
        and status.get("replicas") == status.get("updatedReplicas") == status.get("availableReplicas") == wanted
        and not status.get("unavailableReplicas")
    )
    if not done:
        raise AssertionError(status)
    return deployment


def _restart_worker(kubernetes: KubernetesApi, temporal: TemporalSession[Client]) -> None:
    """Restart the worker and wait until it is rolled out and the schedule exists again."""
    stamp = kubernetes.restart_deployment(NAMESPACE, WORKER)
    wait_until(lambda: _rolled_out(kubernetes, stamp), timeout=RESTART_SECONDS, interval=5, what=f"{WORKER} restarted")
    wait_until(
        lambda: schedule_exists(temporal, SCHEDULE) or None,
        timeout=RESTART_SECONDS,
        interval=5,
        what=f"{SCHEDULE} rebuilt by the restarted worker",
    )


def _recreated(kubernetes: KubernetesApi, temporal: TemporalSession[Client]) -> None:
    """Leave the shared schedule there: a scenario cut short after deleting it restarts the worker once more."""
    if not schedule_exists(temporal, SCHEDULE):
        _restart_worker(kubernetes, temporal)


def _last_discovered(platform: PlatformApi, catalog: str) -> str | None:
    found = [c for c in platform.get("/v1/scanned-catalogs")["catalogs"] if c["catalog"] == catalog]
    if not found or found[0]["last_discovered_at"] is None:
        return None
    return found[0]["last_discovered_at"]


def test_a_restarted_worker_rebuilds_the_deleted_discovery_schedule_and_its_round_scans(
    api: httpx.Client,
    platform: PlatformApi,
    temporal: TemporalSession[Client],
    owned_catalog: OwnedCatalog,
    suffix: str,
    cleanup: CleanupStack,
):
    """The schedule is back, as the worker configures it and not paused; a trigger's round scans the catalog."""
    catalog = owned_catalog.name
    name = OwnedNames.discovery_policy(suffix, "restart")
    platform.call("POST", POLICIES, {"name": name, "description": "e2e", "rules": [NEVER]})
    cleanup.push(f"delete {name}", lambda: _delete_if_present(api, f"{POLICIES}/{name}"))
    on_catalog = {"type": "catalog", "path": [catalog]}
    platform.attach("discovery", name, on_catalog)
    cleanup.push(f"detach {name}", lambda: platform.detach("discovery", name, on_catalog, missing_ok=True))
    wait_until(
        lambda: _last_discovered(platform, catalog),
        timeout=SCAN_SECONDS,
        interval=3,
        what=f"{catalog} scanned, as the attach asks",
    )
    assert schedule_exists(temporal, SCHEDULE)

    kubernetes = KubernetesApi.from_service_account()
    cleanup.push(f"{SCHEDULE} exists again", lambda: _recreated(kubernetes, temporal))

    async def delete(client: Client) -> None:
        await client.get_schedule_handle(SCHEDULE).delete()

    temporal.run(delete)
    assert not schedule_exists(temporal, SCHEDULE)

    _restart_worker(kubernetes, temporal)

    async def describe(client: Client) -> ScheduleDescription:
        return await client.get_schedule_handle(SCHEDULE).describe()

    described = temporal.run(describe)
    assert described.schedule.state.paused is False
    action = described.schedule.action
    assert isinstance(action, ScheduleActionStartWorkflow), action
    assert (action.workflow, action.id) == ("TableDiscoveryRoundWorkflow", ROUND), action
    assert described.schedule.policy.overlap == ScheduleOverlapPolicy.SKIP
    [every] = described.schedule.spec.intervals
    assert every.every == timedelta(seconds=platform.platform_setting("discovery_interval_seconds"))

    scan = f"table-discovery:catalog={catalog}"
    before = wait_until(
        lambda: (
            run if (run := latest_run(temporal, scan)) and run.status == WorkflowExecutionStatus.COMPLETED else None
        ),
        timeout=SCAN_SECONDS,
        interval=3,
        what=f"{scan} completed (the attach's, or a round's since), so the triggered round does not skip it",
    )
    rounds_before = set(scheduled_workflows(temporal, SCHEDULE))
    trigger_schedule(temporal, SCHEDULE)

    def rounds_since() -> list[str]:
        return [w for w in scheduled_workflows(temporal, SCHEDULE) if w not in rounds_before]

    def new_round() -> str:
        started = rounds_since()
        if not started:
            raise AssertionError(f"no round since {sorted(rounds_before)}")
        assert all(w.startswith(f"{ROUND}-") for w in started), started
        return started[-1]

    round_id = wait_until(new_round, timeout=SCAN_SECONDS, interval=3, what=f"a {ROUND} started by the trigger")
    wait_until(
        lambda: (
            run if (run := latest_run(temporal, round_id)) and run.status == WorkflowExecutionStatus.COMPLETED else None
        ),
        timeout=SCAN_SECONDS,
        interval=3,
        what=f"{round_id} completed",
    )

    def scanned_by_the_round() -> WorkflowRun:
        run = latest_run(temporal, scan)
        if run is None or run.run_id == before.run_id or run.status != WorkflowExecutionStatus.COMPLETED:
            raise AssertionError(run)
        return run

    scanned = wait_until(scanned_by_the_round, timeout=SCAN_SECONDS, interval=3, what=f"a new {scan} run completed")
    started = rounds_since()
    assert scanned.parent_id in started, (
        f"{scan} run {scanned.run_id} was started by {scanned.parent_id}, not a round since the trigger: {started}"
    )
