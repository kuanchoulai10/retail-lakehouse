"""Provide the build_gateways function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from adapter.outbound.table.pyiceberg import ReadTableMetadataPyIcebergGateway
from adapter.hybrid.temporal.outbound.table_discovery_settings import (
    UpdateTableDiscoveryScheduleTemporalGateway,
)
from adapter.outbound.table_maintenance_run.k8s import (
    DeleteMaintenanceJobK8sGateway,
    ReadMaintenanceJobK8sGateway,
    SubmitMaintenanceJobK8sGateway,
)
from adapter.hybrid.temporal.outbound.table import (
    SendDiscoveryRequestTemporalGateway,
    SendTableChangeTemporalGateway,
)
from adapter.hybrid.temporal.outbound.table_maintenance_run import (
    SendMaintenanceResultTemporalGateway,
)
from bootstrap.container.build_spark_config import build_spark_config
from bootstrap.container.gateways import Gateways

if TYPE_CHECKING:
    from collections.abc import Callable

    from kubernetes.client import CustomObjectsApi
    from pyiceberg.catalog import Catalog
    from temporalio.client import Client

    from adapter.hybrid.temporal.outbound.shared import AsyncLoopBridge
    from bootstrap.configs import AppSettings


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
        send_table_change=SendTableChangeTemporalGateway(client, bridge),
        send_discovery_request=SendDiscoveryRequestTemporalGateway(client, bridge),
        send_maintenance_result=SendMaintenanceResultTemporalGateway(client, bridge),
        update_table_discovery_schedule=UpdateTableDiscoveryScheduleTemporalGateway(
            client, bridge
        ),
        submit_maintenance_job=SubmitMaintenanceJobK8sGateway(k8s_api, spark_config),
        read_maintenance_job=ReadMaintenanceJobK8sGateway(k8s_api, spark_config),
        delete_maintenance_job=DeleteMaintenanceJobK8sGateway(k8s_api, spark_config),
    )
