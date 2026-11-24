"""A worker that starts rebuilds the discovery schedules the attachments call for.

A catalog of the module's own gets a managing attachment and so a schedule; the scenario deletes the
schedule behind the platform's back, restarts the worker Deployment (the only object the e2e's Role
lets it change) and waits for the schedule to come back. Marked ``full``: a restart takes minutes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from e2e.support import KubernetesApi, OwnedNames, schedule_exists, wait_until

if TYPE_CHECKING:
    import httpx
    from temporalio.client import Client

    from e2e.support import CleanupStack, OwnedCatalog, PlatformApi, TemporalSession

pytestmark = pytest.mark.full

POLICIES = "/v1/discovery-policies"
NAMESPACE = "lakehouse-control-plane"
WORKER = "table-maintenance-worker"
NEVER = {"outcome": "manage", "conditions": [{"attribute": "table_name", "operator": "glob", "values": ["never_*"]}]}
RESTART_SECONDS = 240


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


def test_a_restarted_worker_rebuilds_a_deleted_discovery_schedule(
    api: httpx.Client,
    platform: PlatformApi,
    temporal: TemporalSession[Client],
    owned_catalog: OwnedCatalog,
    suffix: str,
    cleanup: CleanupStack,
):
    """The schedule deleted in Temporal is there again, not paused, once the restarted worker is available."""
    name = OwnedNames.discovery_policy(suffix, "restart")
    platform.call(
        "POST", POLICIES, {"name": name, "description": "e2e", "no_match_outcome": "unmanage", "rules": [NEVER]}
    )
    cleanup.push(f"delete {name}", lambda: _delete_if_present(api, f"{POLICIES}/{name}"))
    attachment = platform.attach("discovery-policies", name, {"type": "catalog", "path": [owned_catalog.name]})
    cleanup.push(f"detach {name}", lambda: _delete_if_present(api, f"{POLICIES}/{name}/attachments/{attachment}"))
    schedule = f"table-discovery:catalog={owned_catalog.name}"
    wait_until(lambda: schedule_exists(temporal, schedule) or None, timeout=60, interval=2, what=f"{schedule} created")

    async def delete(client: Client) -> None:
        await client.get_schedule_handle(schedule).delete()

    temporal.run(delete)
    assert not schedule_exists(temporal, schedule)

    kubernetes = KubernetesApi.from_service_account()
    stamp = kubernetes.restart_deployment(NAMESPACE, WORKER)
    wait_until(lambda: _rolled_out(kubernetes, stamp), timeout=RESTART_SECONDS, interval=5, what=f"{WORKER} restarted")
    wait_until(
        lambda: schedule_exists(temporal, schedule) or None,
        timeout=RESTART_SECONDS,
        interval=5,
        what=f"{schedule} rebuilt by the restarted worker",
    )

    async def paused(client: Client) -> bool:
        return (await client.get_schedule_handle(schedule).describe()).schedule.state.paused

    assert temporal.run(paused) is False
