"""Outbound ports for the table group."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.shared import (
    ComputeSize,
    MaintenanceOperation,
    TablePriority,
)
from context.table_maintenance.application.domain.model.table import (
    TABLE_METRIC_COUNT_FIELDS,
    AppliedPolicyRef,
    AttentionMark,
    OperationState,
    RecordedAttempt,
    Table,
    TableId,
    TableMetrics,
    TableName,
    TableStatus,
)
from context.table_maintenance.application.domain.model.table_discovery_rules import (
    TableDiscoveryRuleId,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    TableMaintenancePolicyId,
    TableMaintenancePolicyName,
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
    "CatalogNotFoundError",
    "MaintenanceOperation",
    "OperationState",
    "RecordedAttempt",
    "TableDiscoveryRuleId",
    "TableId",
    "TableMaintenancePolicyId",
    "TableMaintenancePolicyName",
    "ReadTableMetadataGateway",
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
