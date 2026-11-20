"""Define the ReadMaintenanceJobPodsK8sGateway."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.adapter.outbound.table_maintenance_run.k8s.driver_started_at import (
    driver_started_at,
)
from context.table_maintenance.adapter.outbound.table_maintenance_run.k8s.list_maintenance_job_pods import (
    list_maintenance_job_pods,
)
from context.table_maintenance.application.port.outbound.table_maintenance_run import (
    ReadMaintenanceJobPodsGateway,
    ReadMaintenanceJobPodsGatewayOutput,
)

if TYPE_CHECKING:
    from kubernetes.client import CoreV1Api

    from context.table_maintenance.adapter.outbound.table_maintenance_run.k8s.spark_k8s_config import (
        SparkK8sConfig,
    )
    from context.table_maintenance.application.port.outbound.table_maintenance_run import (
        ReadMaintenanceJobPodsGatewayInput,
    )

STOPPED_PHASES = frozenset({"Succeeded", "Failed"})


class ReadMaintenanceJobPodsK8sGateway(ReadMaintenanceJobPodsGateway):
    """List the driver and executor pods of one attempt by its labels and by its SparkApplication.

    The attempt labels are set on the pods by the manifest; the Spark operator
    also labels every pod it launches with the name of its SparkApplication.
    Both are listed and joined, so the pods of an attempt submitted before the
    attempt labels existed are found too.
    """

    def __init__(self, api: CoreV1Api, config: SparkK8sConfig) -> None:
        """Keep the injected Kubernetes core client and configuration."""
        self._api = api
        self._config = config

    def read(
        self,
        input: ReadMaintenanceJobPodsGatewayInput,  # noqa: A002
    ) -> ReadMaintenanceJobPodsGatewayOutput:
        """Return every pod whose containers can still run, and when the driver container started.

        A pod is live unless its phase is Succeeded or Failed: Pending, Running,
        Unknown and a phase not reported yet all count, and so does a Running pod
        that is being deleted, since it can still write until it is gone. An API
        error propagates, so the caller retries.
        """
        pods = list_maintenance_job_pods(
            self._api, self._config.namespace, input.run_id, input.operation, input.attempt
        )
        return ReadMaintenanceJobPodsGatewayOutput(
            live_pods=tuple(
                pod.metadata.name for pod in pods if pod.status is None or pod.status.phase not in STOPPED_PHASES
            ),
            driver_started_at=driver_started_at(pods),
        )
