"""Define the ReadMaintenanceJobK8sGateway."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.adapter.outbound.table_maintenance_run.k8s.spark_application_manifest import (
    GROUP,
    PLURAL,
    VERSION,
)
from context.table_maintenance.adapter.outbound.table_maintenance_run.k8s.spark_application_name import (
    spark_application_name,
)
from context.table_maintenance.application.port.outbound.table_maintenance_run import (
    ReadMaintenanceJobGateway,
    ReadMaintenanceJobGatewayOutput,
)
from kubernetes.client.exceptions import ApiException

if TYPE_CHECKING:
    from context.table_maintenance.adapter.outbound.table_maintenance_run.k8s.spark_k8s_config import (
        SparkK8sConfig,
    )
    from context.table_maintenance.application.port.outbound.table_maintenance_run import (
        ReadMaintenanceJobGatewayInput,
    )
    from kubernetes.client import CustomObjectsApi

HTTP_NOT_FOUND = 404
FAILED_STATES = frozenset({"FAILED", "SUBMISSION_FAILED", "FAILING"})
RUNNING_STATES = frozenset({"RUNNING", "PENDING_RERUN", "INVALIDATING", "SUCCEEDING"})


class ReadMaintenanceJobK8sGateway(ReadMaintenanceJobGateway):
    """Read the state of a SparkApplication."""

    def __init__(self, api: CustomObjectsApi, config: SparkK8sConfig) -> None:
        """Keep the injected Kubernetes client and configuration."""
        self._api = api
        self._config = config

    def read(
        self,
        input: ReadMaintenanceJobGatewayInput,  # noqa: A002
    ) -> ReadMaintenanceJobGatewayOutput:
        """Map the SparkApplication state to the port vocabulary."""
        try:
            app = self._api.get_namespaced_custom_object(
                group=GROUP,
                version=VERSION,
                namespace=self._config.namespace,
                plural=PLURAL,
                name=spark_application_name(input.run_id, input.operation, input.attempt),
            )
        except ApiException as exc:
            if exc.status == HTTP_NOT_FOUND:
                return ReadMaintenanceJobGatewayOutput("NOT_FOUND")
            raise
        application_state = (app.get("status") or {}).get("applicationState") or {}
        state = application_state.get("state") or ""
        if state == "COMPLETED":
            return ReadMaintenanceJobGatewayOutput("COMPLETED")
        if state in FAILED_STATES:
            return ReadMaintenanceJobGatewayOutput("FAILED", application_state.get("errorMessage"))
        if state in RUNNING_STATES:
            return ReadMaintenanceJobGatewayOutput("RUNNING")
        return ReadMaintenanceJobGatewayOutput("PENDING")
