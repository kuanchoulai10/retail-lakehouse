"""Provide the build_gateways function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bootstrap.container.build_event_log_filesystem import build_event_log_filesystem
from bootstrap.container.build_spark_config import build_spark_config
from bootstrap.container.event_log_base import event_log_base
from bootstrap.container.gateways import Gateways
from context.table_maintenance.adapter.hybrid.temporal.outbound.table import (
    SendDiscoveryRequestTemporalGateway,
    SendTableChangeTemporalGateway,
)
from context.table_maintenance.adapter.hybrid.temporal.outbound.table_maintenance_run import (
    SendMaintenanceResultTemporalGateway,
)
from context.table_maintenance.adapter.outbound.table.pyiceberg import (
    ReadTableMetadataPyIcebergGateway,
)
from context.table_maintenance.adapter.outbound.table_maintenance_run.k8s import (
    DeleteMaintenanceJobK8sGateway,
    ReadMaintenanceJobEvidenceK8sGateway,
    ReadMaintenanceJobK8sGateway,
    ReadMaintenanceJobPodsK8sGateway,
    SubmitMaintenanceJobK8sGateway,
)
from context.table_maintenance.adapter.outbound.table_maintenance_run.s3 import (
    ReadMaintenanceEventLogS3Gateway,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from kubernetes.client import CoreV1Api, CustomObjectsApi
    from pyiceberg.catalog import Catalog
    from temporalio.client import Client

    from bootstrap.configs import AppSettings
    from context.table_maintenance.adapter.hybrid.temporal.outbound.shared import (
        AsyncLoopBridge,
    )


def build_gateways(
    settings: AppSettings,
    *,
    client: Client,
    bridge: AsyncLoopBridge,
    k8s_api: CustomObjectsApi,
    k8s_core_api: CoreV1Api,
    catalog_factory: Callable[[str], Catalog],
) -> Gateways:
    """Build the production gateways; nothing connects here.

    ``client`` must have been connected on ``bridge``'s loop, because the Temporal
    gateways run every call on that loop. The event log file system is built on first use,
    so a component that never reads an event log never builds it.
    """
    spark_config = build_spark_config(settings)
    return Gateways(
        read_table_metadata=ReadTableMetadataPyIcebergGateway(catalog_factory),
        send_table_change=SendTableChangeTemporalGateway(client, bridge),
        send_discovery_request=SendDiscoveryRequestTemporalGateway(client, bridge),
        send_maintenance_result=SendMaintenanceResultTemporalGateway(client, bridge),
        submit_maintenance_job=SubmitMaintenanceJobK8sGateway(k8s_api, spark_config),
        read_maintenance_job=ReadMaintenanceJobK8sGateway(k8s_api, spark_config),
        delete_maintenance_job=DeleteMaintenanceJobK8sGateway(k8s_api, spark_config),
        read_maintenance_job_pods=ReadMaintenanceJobPodsK8sGateway(k8s_core_api, spark_config),
        read_maintenance_job_evidence=ReadMaintenanceJobEvidenceK8sGateway(k8s_api, k8s_core_api, spark_config),
        read_maintenance_event_log=ReadMaintenanceEventLogS3Gateway(
            lambda: build_event_log_filesystem(settings), event_log_base(settings)
        ),
    )
