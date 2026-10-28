"""Outbound ports for the table group."""

from __future__ import annotations

from application.domain.model.table import Table, TableId, TableName, TableStatus
from application.port.outbound.table.read_table_metadata.gateway import (
    ReadTableMetadataGateway,
)
from application.port.outbound.table.read_table_metadata.list_input import (
    ReadTableMetadataGatewayListInput,
)
from application.port.outbound.table.read_table_metadata.table_metadata import (
    TableMetadata,
)
from application.port.outbound.table.read_table_metadata.table_metadata_observation import (
    TableMetadataObservation,
)
from application.port.outbound.table.read_table_metadata.table_metadata_ref import (
    TableMetadataRef,
)
from application.port.outbound.table.send_discovery_request.gateway import (
    SendDiscoveryRequestGateway,
)
from application.port.outbound.table.send_discovery_request.input import (
    SendDiscoveryRequestGatewayInput,
)
from application.port.outbound.table.send_table_change.gateway import (
    SendTableChangeGateway,
)
from application.port.outbound.table.send_table_change.input import (
    SendTableChangeGatewayInput,
)
from application.port.outbound.table.tables_repo import TablesRepo

__all__ = [
    "TableId",
    "ReadTableMetadataGateway",
    "ReadTableMetadataGatewayListInput",
    "SendDiscoveryRequestGateway",
    "SendDiscoveryRequestGatewayInput",
    "SendTableChangeGateway",
    "SendTableChangeGatewayInput",
    "Table",
    "TableMetadata",
    "TableMetadataObservation",
    "TableMetadataRef",
    "TableName",
    "TableStatus",
    "TablesRepo",
]
