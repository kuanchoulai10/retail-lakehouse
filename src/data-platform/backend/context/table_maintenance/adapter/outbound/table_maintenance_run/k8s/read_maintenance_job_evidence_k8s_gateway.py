"""Define the ReadMaintenanceJobEvidenceK8sGateway."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kubernetes.client.exceptions import ApiException

from context.table_maintenance.adapter.outbound.table_maintenance_run.k8s.driver_started_at import (
    SPARK_ROLE_LABEL,
    driver_started_at,
)
from context.table_maintenance.adapter.outbound.table_maintenance_run.k8s.list_maintenance_job_pods import (
    list_maintenance_job_pods,
)
from context.table_maintenance.adapter.outbound.table_maintenance_run.k8s.spark_application_manifest import (
    GROUP,
    PLURAL,
    VERSION,
)
from context.table_maintenance.adapter.outbound.table_maintenance_run.k8s.spark_application_name import (
    spark_application_name,
)
from context.table_maintenance.application.port.outbound.table_maintenance_run import (
    JobContainerExit,
    ReadMaintenanceJobEvidenceGateway,
    ReadMaintenanceJobEvidenceGatewayOutput,
)

if TYPE_CHECKING:
    from kubernetes.client import CoreV1Api, CustomObjectsApi, V1ContainerStatus, V1Pod

    from context.table_maintenance.adapter.outbound.table_maintenance_run.k8s.spark_k8s_config import (
        SparkK8sConfig,
    )
    from context.table_maintenance.application.port.outbound.table_maintenance_run import (
        ReadMaintenanceJobEvidenceGatewayInput,
    )

HTTP_NOT_FOUND = 404
SPARK_CONTAINERS = frozenset({"spark-kubernetes-driver", "spark-kubernetes-executor"})


class ReadMaintenanceJobEvidenceK8sGateway(ReadMaintenanceJobEvidenceGateway):
    """Read an attempt's SparkApplication status and how its driver and executor containers terminated.

    Executor pods are kept after they end (the manifest turns off their deletion), so a
    failed attempt's executors can be read until its SparkApplication is deleted.
    """

    def __init__(self, custom_api: CustomObjectsApi, core_api: CoreV1Api, config: SparkK8sConfig) -> None:
        """Keep the injected Kubernetes clients and configuration."""
        self._custom_api = custom_api
        self._core_api = core_api
        self._config = config

    def read(
        self,
        input: ReadMaintenanceJobEvidenceGatewayInput,  # noqa: A002
    ) -> ReadMaintenanceJobEvidenceGatewayOutput:
        """Return the application id and error, and every terminated Spark container of the attempt's pods.

        A SparkApplication that is gone gives no id and no error; other API errors propagate.
        """
        execution_id, error = self._application_status(input)
        pods = list_maintenance_job_pods(
            self._core_api, self._config.namespace, input.run_id, input.operation, input.attempt
        )
        containers = tuple(exit_ for exit_ in (_container_exit(pod) for pod in pods) if exit_ is not None)
        return ReadMaintenanceJobEvidenceGatewayOutput(
            execution_id=execution_id, error=error, containers=containers, started_running_at=driver_started_at(pods)
        )

    def _application_status(self, input: ReadMaintenanceJobEvidenceGatewayInput) -> tuple[str | None, str | None]:  # noqa: A002
        try:
            app = self._custom_api.get_namespaced_custom_object(
                group=GROUP,
                version=VERSION,
                namespace=self._config.namespace,
                plural=PLURAL,
                name=spark_application_name(input.run_id, input.operation, input.attempt),
            )
        except ApiException as exc:
            if exc.status == HTTP_NOT_FOUND:
                return None, None
            raise
        status = app.get("status") or {}
        application_state = status.get("applicationState") or {}
        return status.get("sparkApplicationId"), application_state.get("errorMessage")


def _spark_status(pod: V1Pod) -> V1ContainerStatus | None:
    statuses = (pod.status.container_statuses if pod.status else None) or []
    return next((s for s in statuses if s.name in SPARK_CONTAINERS), statuses[0] if statuses else None)


# The Spark role of a pod, as the job's coordinator or one of its workers.
_ROLES = {"driver": "coordinator", "executor": "worker"}


def _container_exit(pod: V1Pod) -> JobContainerExit | None:
    """Return how the pod's Spark container terminated, or None while it has not."""
    status = _spark_status(pod)
    if status is None:
        return None
    terminated = (status.state.terminated if status.state else None) or (
        status.last_state.terminated if status.last_state else None
    )
    if terminated is None:
        return None
    return JobContainerExit(
        role=_ROLES.get((pod.metadata.labels or {}).get(SPARK_ROLE_LABEL, ""), ""),
        reason=terminated.reason,
        exit_code=terminated.exit_code,
        message=terminated.message,
    )
