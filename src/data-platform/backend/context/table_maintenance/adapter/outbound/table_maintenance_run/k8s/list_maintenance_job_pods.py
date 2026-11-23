"""Define the list_maintenance_job_pods function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.adapter.outbound.table_maintenance_run.k8s.maintenance_job_pod_labels import (
    maintenance_job_pod_labels,
)

if TYPE_CHECKING:
    from kubernetes.client import CoreV1Api, V1Pod


def list_maintenance_job_pods(api: CoreV1Api, namespace: str, run_id: str, operation: str, attempt: int) -> list[V1Pod]:
    """Return the pods of one attempt, found by the attempt labels the manifest puts on them.

    An API error propagates.
    """
    labels = maintenance_job_pod_labels(run_id, operation, attempt)
    selector = ",".join(f"{key}={value}" for key, value in labels.items())
    return list(api.list_namespaced_pod(namespace=namespace, label_selector=selector).items)
