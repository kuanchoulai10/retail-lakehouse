"""Provide job_pod_group, which finds the PodGroup the Spark operator made for one maintenance job."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from e2e.support.kubernetes_api import KubernetesApi

PODGROUPS = "/apis/scheduling.volcano.sh/v1beta1/namespaces/lakehouse-maintenance-operations/podgroups"


def job_pod_group(kubernetes: KubernetesApi, job_name: str) -> dict[str, Any] | None:
    """Return the PodGroup owned by the SparkApplication ``job_name``, or None while there is none.

    The group's name is the operator's to choose, so it is found by its owner instead.
    """
    owned = [
        group
        for group in kubernetes.list(PODGROUPS)["items"]
        if any(owner.get("name") == job_name for owner in group["metadata"].get("ownerReferences", []))
    ]
    assert len(owned) <= 1, f"PodGroups of {job_name}: {[group['metadata']['name'] for group in owned]}"
    return owned[0] if owned else None
