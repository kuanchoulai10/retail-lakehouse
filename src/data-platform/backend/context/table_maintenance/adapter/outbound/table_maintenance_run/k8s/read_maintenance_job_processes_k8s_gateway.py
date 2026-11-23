"""Define the ReadMaintenanceJobProcessesK8sGateway."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.adapter.outbound.table_maintenance_run.k8s.driver_started_at import (
    driver_started_at,
)
from context.table_maintenance.adapter.outbound.table_maintenance_run.k8s.list_maintenance_job_pods import (
    list_maintenance_job_pods,
)
from context.table_maintenance.application.port.outbound.table_maintenance_run import (
    ReadMaintenanceJobProcessesGateway,
    ReadMaintenanceJobProcessesGatewayOutput,
)

if TYPE_CHECKING:
    from kubernetes.client import CoreV1Api

    from context.table_maintenance.adapter.outbound.table_maintenance_run.k8s.spark_k8s_config import (
        SparkK8sConfig,
    )
    from context.table_maintenance.application.port.outbound.table_maintenance_run import (
        ReadMaintenanceJobProcessesGatewayInput,
    )

STOPPED_PHASES = frozenset({"Succeeded", "Failed"})


class ReadMaintenanceJobProcessesK8sGateway(ReadMaintenanceJobProcessesGateway):
    """List the driver and executor pods of one attempt by the attempt labels the manifest sets on them."""

    def __init__(self, api: CoreV1Api, config: SparkK8sConfig) -> None:
        """Keep the injected Kubernetes core client and configuration."""
        self._api = api
        self._config = config

    def read(
        self,
        input: ReadMaintenanceJobProcessesGatewayInput,  # noqa: A002
    ) -> ReadMaintenanceJobProcessesGatewayOutput:
        """Return every pod whose containers can still run, and when the driver container started.

        A pod is live unless its phase is Succeeded or Failed: Pending, Running,
        Unknown and a phase not reported yet all count, and so does a Running pod
        that is being deleted, since it can still write until it is gone. An API
        error propagates, so the caller retries.
        """
        pods = list_maintenance_job_pods(
            self._api, self._config.namespace, input.run_id, input.operation, input.attempt
        )
        return ReadMaintenanceJobProcessesGatewayOutput(
            live_processes=tuple(
                pod.metadata.name for pod in pods if pod.status is None or pod.status.phase not in STOPPED_PHASES
            ),
            started_running_at=driver_started_at(pods),
        )
