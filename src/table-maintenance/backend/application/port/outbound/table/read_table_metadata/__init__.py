"""Read tables and their statistics from the catalog."""

from application.port.outbound.table.read_table_metadata.gateway import (
    ReadTableMetadataGateway,
)
from application.port.outbound.table.read_table_metadata.list_input import (
    ReadTableMetadataGatewayListInput,
)
from application.port.outbound.table.read_table_metadata.table_metadata_observation import (
    TableMetadataObservation,
)
from application.port.outbound.table.read_table_metadata.table_metadata import (
    TableMetadata,
)
from application.port.outbound.table.read_table_metadata.table_metadata_ref import (
    TableMetadataRef,
)

__all__ = [
    "ReadTableMetadataGateway",
    "ReadTableMetadataGatewayListInput",
    "TableMetadataObservation",
    "TableMetadata",
    "TableMetadataRef",
]
