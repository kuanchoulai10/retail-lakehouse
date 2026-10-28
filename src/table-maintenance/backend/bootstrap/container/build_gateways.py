"""Provide the build_gateways function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from adapter.outbound.table.pyiceberg.read_table_metadata_pyiceberg_gateway import (
    ReadTableMetadataPyIcebergGateway,
)
from adapter.outbound.table_discovery_settings.temporal.update_table_discovery_schedule_temporal_gateway import (
    UpdateTableDiscoveryScheduleTemporalGateway,
)
from adapter.outbound.spark.k8s.delete_maintenance_job_k8s_gateway import (
    DeleteMaintenanceJobK8sGateway,
)
from adapter.outbound.spark.k8s.read_maintenance_job_k8s_gateway import (
    ReadMaintenanceJobK8sGateway,
)
from adapter.outbound.spark.k8s.submit_maintenance_job_k8s_gateway import (
    SubmitMaintenanceJobK8sGateway,
)
from adapter.outbound.workflow.temporal.send_discovery_request_temporal_gateway import (
    SendDiscoveryRequestTemporalGateway,
)
from adapter.outbound.workflow.temporal.send_maintenance_result_temporal_gateway import (
    SendMaintenanceResultTemporalGateway,
)
from adapter.outbound.workflow.temporal.send_table_signal_temporal_gateway import (
    SendTableSignalTemporalGateway,
)
from bootstrap.container.build_spark_config import build_spark_config
from bootstrap.container.gateways import Gateways

if TYPE_CHECKING:
    from collections.abc import Callable

    from kubernetes.client import CustomObjectsApi
    from pyiceberg.catalog import Catalog
    from temporalio.client import Client

    from adapter.outbound.temporal.async_loop_bridge import AsyncLoopBridge
    from bootstrap.configs.app_settings import AppSettings


def build_gateways(
    settings: AppSettings,
    *,
    client: Client,
    bridge: AsyncLoopBridge,
    k8s_api: CustomObjectsApi,
    catalog_factory: Callable[[str], Catalog],
) -> Gateways:
    """Build the production gateways; nothing connects here.

    ``client`` must have been connected on ``bridge``'s loop, because the Temporal
    gateways run every call on that loop.
    """
    spark_config = build_spark_config(settings)
    return Gateways(
        read_table_metadata=ReadTableMetadataPyIcebergGateway(catalog_factory),
        send_table_signal=SendTableSignalTemporalGateway(client, bridge),
        send_discovery_request=SendDiscoveryRequestTemporalGateway(client, bridge),
        send_maintenance_result=SendMaintenanceResultTemporalGateway(client, bridge),
        update_table_discovery_schedule=UpdateTableDiscoveryScheduleTemporalGateway(
            client, bridge
        ),
        submit_maintenance_job=SubmitMaintenanceJobK8sGateway(k8s_api, spark_config),
        read_maintenance_job=ReadMaintenanceJobK8sGateway(k8s_api, spark_config),
        delete_maintenance_job=DeleteMaintenanceJobK8sGateway(k8s_api, spark_config),
    )
