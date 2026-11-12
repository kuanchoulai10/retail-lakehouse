"""Define the list_maintenance_job_pods function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.adapter.outbound.table_maintenance_run.k8s.maintenance_job_pod_labels import (
    maintenance_job_pod_labels,
)
from context.table_maintenance.adapter.outbound.table_maintenance_run.k8s.spark_application_name import (
    spark_application_name,
)

if TYPE_CHECKING:
    from kubernetes.client import CoreV1Api, V1Pod

SPARK_OPERATOR_APP_LABEL = "sparkoperator.k8s.io/app-name"


def list_maintenance_job_pods(api: CoreV1Api, namespace: str, run_id: str, operation: str, attempt: int) -> list[V1Pod]:
    """Return the pods of one attempt, found by its labels or by its SparkApplication, each once.

    The attempt labels are set on the pods by the manifest; the Spark operator also labels
    every pod it launches with the name of its SparkApplication. Both are listed and joined,
    so the pods of an attempt submitted before the attempt labels existed are found too. An
    API error propagates.
    """
    labels = maintenance_job_pod_labels(run_id, operation, attempt)
    application = spark_application_name(run_id, operation, attempt)
    selectors = (
        ",".join(f"{key}={value}" for key, value in labels.items()),
        f"{SPARK_OPERATOR_APP_LABEL}={application}",
    )
    found: dict[str, V1Pod] = {}
    for selector in selectors:
        for pod in api.list_namespaced_pod(namespace=namespace, label_selector=selector).items:
            found.setdefault(pod.metadata.name, pod)
    return list(found.values())
