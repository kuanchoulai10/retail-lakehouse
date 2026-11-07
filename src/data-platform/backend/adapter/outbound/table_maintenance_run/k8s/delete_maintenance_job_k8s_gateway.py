"""Define the DeleteMaintenanceJobK8sGateway."""

from __future__ import annotations

from typing import TYPE_CHECKING

from adapter.outbound.table_maintenance_run.k8s.spark_application_manifest import (
    GROUP,
    PLURAL,
    VERSION,
)
from adapter.outbound.table_maintenance_run.k8s.spark_application_name import (
    spark_application_name,
)
from application.port.outbound.table_maintenance_run import DeleteMaintenanceJobGateway
from kubernetes.client.exceptions import ApiException

if TYPE_CHECKING:
    from adapter.outbound.table_maintenance_run.k8s.spark_k8s_config import (
        SparkK8sConfig,
    )
    from application.port.outbound.table_maintenance_run import (
        DeleteMaintenanceJobGatewayInput,
    )
    from kubernetes.client import CustomObjectsApi

HTTP_NOT_FOUND = 404


class DeleteMaintenanceJobK8sGateway(DeleteMaintenanceJobGateway):
    """Delete a SparkApplication."""

    def __init__(self, api: CustomObjectsApi, config: SparkK8sConfig) -> None:
        """Keep the injected Kubernetes client and configuration."""
        self._api = api
        self._config = config

    def delete(self, input: DeleteMaintenanceJobGatewayInput) -> None:  # noqa: A002
        """Delete the SparkApplication; a missing one is a no-op."""
        try:
            self._api.delete_namespaced_custom_object(
                group=GROUP,
                version=VERSION,
                namespace=self._config.namespace,
                plural=PLURAL,
                name=spark_application_name(
                    input.run_id, input.operation, input.attempt
                ),
            )
        except ApiException as exc:
            if exc.status != HTTP_NOT_FOUND:
                raise
