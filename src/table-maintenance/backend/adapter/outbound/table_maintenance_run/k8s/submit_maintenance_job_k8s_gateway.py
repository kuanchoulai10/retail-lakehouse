"""Define the SubmitMaintenanceJobK8sGateway."""

from __future__ import annotations

from typing import TYPE_CHECKING

from adapter.outbound.table_maintenance_run.k8s.spark_application_manifest import (
    GROUP,
    PLURAL,
    VERSION,
    build_spark_application,
)
from adapter.outbound.table_maintenance_run.k8s.spark_application_name import (
    spark_application_name,
)
from application.port.outbound.table_maintenance_run.submit_maintenance_job import (
    SubmitMaintenanceJobGateway,
    SubmitMaintenanceJobGatewayOutput,
)
from kubernetes.client.exceptions import ApiException

if TYPE_CHECKING:
    from adapter.outbound.table_maintenance_run.k8s.spark_k8s_config import (
        SparkK8sConfig,
    )
    from application.port.outbound.table_maintenance_run.submit_maintenance_job import (
        SubmitMaintenanceJobGatewayInput,
    )
    from kubernetes.client import CustomObjectsApi

HTTP_CONFLICT = 409


class SubmitMaintenanceJobK8sGateway(SubmitMaintenanceJobGateway):
    """Submit a maintenance job as a SparkApplication."""

    def __init__(self, api: CustomObjectsApi, config: SparkK8sConfig) -> None:
        """Keep the injected Kubernetes client and configuration."""
        self._api = api
        self._config = config

    def submit(
        self,
        input: SubmitMaintenanceJobGatewayInput,  # noqa: A002
    ) -> SubmitMaintenanceJobGatewayOutput:
        """Create the SparkApplication; an existing one counts as submitted."""
        name = spark_application_name(input.run_id, input.operation, input.attempt)
        body = build_spark_application(self._config, input, name)
        try:
            self._api.create_namespaced_custom_object(
                group=GROUP,
                version=VERSION,
                namespace=self._config.namespace,
                plural=PLURAL,
                body=body,
            )
        except ApiException as exc:
            if exc.status != HTTP_CONFLICT:
                raise
        return SubmitMaintenanceJobGatewayOutput(job_name=name)
