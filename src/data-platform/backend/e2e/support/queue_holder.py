"""Provide QueueHolder, a PodGroup with no pods that fills a Volcano queue so the next job waits."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from e2e.support.cleanup_stack import CleanupStack
    from e2e.support.kubernetes_api import KubernetesApi

PODGROUPS = "/apis/scheduling.volcano.sh/v1beta1/namespaces/lakehouse-maintenance-operations/podgroups"
HOLDER_SELECTOR = "app.kubernetes.io/name=table-maintenance-e2e,app.kubernetes.io/component=queue-holder"


class QueueHolder:
    """Hold a queue as long as the scenario wants: Volcano admits the holder and counts its request.

    The holder asks the queue's whole capability (cpu 2), so a Spark job's PodGroup stays Pending
    until the holder is deleted. It has no pod, so it runs nothing and needs no ServiceAccount.
    A holder left behind blocks every run of the queue: its undo is pushed before it is created,
    and the session sweep deletes holders by their labels.
    """

    def __init__(self, kubernetes: KubernetesApi, name: str) -> None:
        """Refer to the holder ``name``."""
        self._kubernetes = kubernetes
        self.name = name

    @classmethod
    def create(
        cls, kubernetes: KubernetesApi, cleanup: CleanupStack, name: str, *, queue: str = "table-maintenance"
    ) -> QueueHolder:
        """Fill ``queue`` with the holder ``name`` (from ``OwnedNames.queue_holder``)."""
        holder = cls(kubernetes, name)
        cleanup.push(f"release queue holder {name}", holder.release)
        kubernetes.create(
            PODGROUPS,
            {
                "apiVersion": "scheduling.volcano.sh/v1beta1",
                "kind": "PodGroup",
                "metadata": {
                    "name": name,
                    "labels": {
                        "app.kubernetes.io/name": "table-maintenance-e2e",
                        "app.kubernetes.io/component": "queue-holder",
                    },
                },
                "spec": {"minMember": 1, "queue": queue, "minResources": {"cpu": "2", "memory": "2304Mi"}},
            },
        )
        return holder

    def phase(self) -> str | None:
        """Return the holder's Volcano phase (``Inqueue`` once it holds the queue), ``None`` once gone."""
        found = self._kubernetes.get(f"{PODGROUPS}/{self.name}")
        return None if found is None else found.get("status", {}).get("phase")

    def release(self) -> None:
        """Delete the holder so the queue admits the next job; releasing twice is fine."""
        self._kubernetes.delete(f"{PODGROUPS}/{self.name}")
