"""Outbound ports for the table group."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.shared import (
    ComputeSize,
    MaintenanceOperation,
    OverTargetPartition,
    PolicyTarget,
    TableDiscoveryPolicyId,
    TableDiscoveryRuleId,
    TableId,
    TableMaintenancePolicyId,
    TableMaintenanceRunId,
    TablePriority,
)
from context.table_maintenance.application.domain.model.table import (
    TABLE_METRIC_COUNT_FIELDS,
    AppliedPolicyRef,
    AttentionMark,
    OperationState,
    RecordedAttempt,
    Table,
    TableMetrics,
    TableName,
    TableStatus,
)
from context.table_maintenance.application.domain.model.table_discovery_policy import DiscoveryMatch
from context.table_maintenance.application.domain.model.table_maintenance_policy import TableMaintenancePolicyName
from context.table_maintenance.application.port.outbound.table.read_table_metadata.catalog_access_denied_error import (  # noqa: E501
    CatalogAccessDeniedError,
)
from context.table_maintenance.application.port.outbound.table.read_table_metadata.catalog_not_found_error import (
    CatalogNotFoundError,
)
from context.table_maintenance.application.port.outbound.table.read_table_metadata.gateway import (
    ReadTableMetadataGateway,
)
from context.table_maintenance.application.port.outbound.table.read_table_metadata.list_input import (
    ReadTableMetadataGatewayListInput,
)
from context.table_maintenance.application.port.outbound.table.read_table_metadata.table_commit_page import (
    TableCommitPage,
)
from context.table_maintenance.application.port.outbound.table.read_table_metadata.table_commit_selection import (
    TableCommitSelection,
)
from context.table_maintenance.application.port.outbound.table.read_table_metadata.table_metadata import (
    TableMetadata,
)
from context.table_maintenance.application.port.outbound.table.read_table_metadata.table_metadata_observation import (
    TableMetadataObservation,
)
from context.table_maintenance.application.port.outbound.table.read_table_metadata.table_metadata_ref import (
    TableMetadataRef,
)
from context.table_maintenance.application.port.outbound.table.read_table_metric_history.gateway import (
    ReadTableMetricHistoryGateway,
)
from context.table_maintenance.application.port.outbound.table.read_table_metric_history.input import (
    ReadTableMetricHistoryGatewayInput,
)
from context.table_maintenance.application.port.outbound.table.read_table_metric_history.metric_history_unavailable_error import (  # noqa: E501
    MetricHistoryUnavailableError,
)
from context.table_maintenance.application.port.outbound.table.read_table_metric_history.output import (
    ReadTableMetricHistoryGatewayOutput,
)
from context.table_maintenance.application.port.outbound.table.send_discovery_request.gateway import (
    SendDiscoveryRequestGateway,
)
from context.table_maintenance.application.port.outbound.table.send_discovery_request.input import (
    SendDiscoveryRequestGatewayInput,
)
from context.table_maintenance.application.port.outbound.table.send_table_change.gateway import (
    SendTableChangeGateway,
)
from context.table_maintenance.application.port.outbound.table.send_table_change.input import (
    SendTableChangeGatewayInput,
)
from context.table_maintenance.application.port.outbound.table.table_metrics_store import (
    TableMetricsStore,
)
from context.table_maintenance.application.port.outbound.table.tables_repo import (
    TablesRepo,
)

__all__ = [
    "TABLE_METRIC_COUNT_FIELDS",
    "AppliedPolicyRef",
    "AttentionMark",
    "ComputeSize",
    "CatalogAccessDeniedError",
    "CatalogNotFoundError",
    "MaintenanceOperation",
    "MetricHistoryUnavailableError",
    "OperationState",
    "OverTargetPartition",
    "PolicyTarget",
    "RecordedAttempt",
    "DiscoveryMatch",
    "TableDiscoveryPolicyId",
    "TableDiscoveryRuleId",
    "TableId",
    "TableMaintenancePolicyId",
    "TableMaintenanceRunId",
    "TableMaintenancePolicyName",
    "ReadTableMetadataGateway",
    "ReadTableMetricHistoryGateway",
    "ReadTableMetricHistoryGatewayInput",
    "ReadTableMetricHistoryGatewayOutput",
    "TableCommitSelection",
    "ReadTableMetadataGatewayListInput",
    "SendDiscoveryRequestGateway",
    "SendDiscoveryRequestGatewayInput",
    "SendTableChangeGateway",
    "SendTableChangeGatewayInput",
    "Table",
    "TableCommitPage",
    "TableMetadata",
    "TableMetadataObservation",
    "TableMetadataRef",
    "TableMetrics",
    "TableMetricsStore",
    "TableName",
    "TablePriority",
    "TableStatus",
    "TablesRepo",
]
