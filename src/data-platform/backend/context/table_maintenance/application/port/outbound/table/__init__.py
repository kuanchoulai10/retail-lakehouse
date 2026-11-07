"""Outbound ports for the table group."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation,
)
from context.table_maintenance.application.domain.model.table import (
    OperationState,
    TableSelection,
)
from context.table_maintenance.application.domain.model.table_discovery_rule import (
    TableDiscoveryRuleId,
)
from context.table_maintenance.application.domain.model.table_maintenance_preset import (
    TableMaintenancePresetId,
)
from context.table_maintenance.application.domain.model.table import (
    Table,
    TableId,
    TableName,
    TableStatus,
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
from context.table_maintenance.application.port.outbound.table.read_table_metadata.table_description import (
    TableDescription,
)
from context.table_maintenance.application.port.outbound.table.read_table_metadata.table_storage_measure import (
    TableStorageMeasure,
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
from context.table_maintenance.application.port.outbound.table.tables_repo import (
    TablesRepo,
)

__all__ = [
    "MaintenanceOperation",
    "OperationState",
    "TableSelection",
    "TableDiscoveryRuleId",
    "TableMaintenancePresetId",
    "TableId",
    "ReadTableMetadataGateway",
    "ReadTableMetadataGatewayListInput",
    "SendDiscoveryRequestGateway",
    "SendDiscoveryRequestGatewayInput",
    "SendTableChangeGateway",
    "SendTableChangeGatewayInput",
    "Table",
    "TableCommitPage",
    "TableDescription",
    "TableStorageMeasure",
    "TableMetadata",
    "TableMetadataObservation",
    "TableMetadataRef",
    "TableName",
    "TableStatus",
    "TablesRepo",
]
