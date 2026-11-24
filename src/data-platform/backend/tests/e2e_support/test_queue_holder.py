"""Test QueueHolder, a pod-less PodGroup that keeps a Volcano queue full while a scenario wants it held."""

from __future__ import annotations

import json

import httpx

from e2e.support import CleanupStack, KubernetesApi, QueueHolder

PODGROUPS = "/apis/scheduling.volcano.sh/v1beta1/namespaces/lakehouse-maintenance-operations/podgroups"


def _api(seen: list[tuple[str, str, object]], phase: str = "Inqueue") -> KubernetesApi:
    def handle(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, request.url.path, json.loads(request.content) if request.content else None))
        if request.method == "GET":
            return httpx.Response(200, json={"status": {"phase": phase}})
        return httpx.Response(404 if request.method == "DELETE" and len(seen) > 3 else 200, json={})

    return KubernetesApi(httpx.Client(transport=httpx.MockTransport(handle), base_url="https://kubernetes"))


def test_a_holder_asks_for_the_whole_queue_and_its_undo_is_pushed_first():
    """The PodGroup asks the queue's capability (cpu 2) and carries the labels the sweep finds it by."""
    seen: list[tuple[str, str, object]] = []
    cleanup = CleanupStack()
    holder = QueueHolder.create(_api(seen), cleanup, "tm-e2e-holder-1a2b3c4d-queue")
    [(method, path, body)] = seen
    assert (method, path) == ("POST", PODGROUPS)
    assert body == {
        "apiVersion": "scheduling.volcano.sh/v1beta1",
        "kind": "PodGroup",
        "metadata": {
            "name": "tm-e2e-holder-1a2b3c4d-queue",
            "labels": {
                "app.kubernetes.io/name": "table-maintenance-e2e",
                "app.kubernetes.io/component": "queue-holder",
            },
        },
        "spec": {"minMember": 1, "queue": "table-maintenance", "minResources": {"cpu": "2", "memory": "2304Mi"}},
    }
    assert holder.phase() == "Inqueue"
    cleanup.run()
    assert seen[-1][:2] == ("DELETE", f"{PODGROUPS}/tm-e2e-holder-1a2b3c4d-queue")


def test_releasing_twice_is_fine():
    """The scenario releases the hold itself; the undo then finds nothing to delete."""
    seen: list[tuple[str, str, object]] = []
    cleanup = CleanupStack()
    holder = QueueHolder.create(_api(seen), cleanup, "tm-e2e-holder-1a2b3c4d-queue")
    holder.release()
    holder.release()
    cleanup.run()
    assert [method for method, _, _ in seen] == ["POST", "DELETE", "DELETE", "DELETE"]
