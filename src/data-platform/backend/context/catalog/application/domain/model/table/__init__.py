"""Table domain vocabulary: the Iceberg table aggregate, its value objects and the known table properties."""

from __future__ import annotations

from context.catalog.application.domain.model.table.default_partition_field_names import (
    DefaultPartitionFieldNames,
)
from context.catalog.application.domain.model.table.iceberg_table_property_catalogue import (
    iceberg_table_property_catalogue,
)
from context.catalog.application.domain.model.table.null_order import NullOrder
from context.catalog.application.domain.model.table.partition_change import PartitionChange
from context.catalog.application.domain.model.table.partition_field import PartitionField
from context.catalog.application.domain.model.table.partition_field_comparison import PartitionFieldComparison
from context.catalog.application.domain.model.table.partition_spec import PartitionSpec
from context.catalog.application.domain.model.table.partition_spec_comparison import PartitionSpecComparison
from context.catalog.application.domain.model.table.partition_transform import PartitionTransform
from context.catalog.application.domain.model.table.partition_transform_kind import PartitionTransformKind
from context.catalog.application.domain.model.table.schema_change import SchemaChange
from context.catalog.application.domain.model.table.schema_comparison import SchemaComparison
from context.catalog.application.domain.model.table.schema_field_comparison import SchemaFieldComparison
from context.catalog.application.domain.model.table.snapshot import Snapshot
from context.catalog.application.domain.model.table.sort_direction import SortDirection
from context.catalog.application.domain.model.table.sort_field import SortField
from context.catalog.application.domain.model.table.sort_order import SortOrder
from context.catalog.application.domain.model.table.table import Table
from context.catalog.application.domain.model.table.table_id import TableId
from context.catalog.application.domain.model.table.table_property import TableProperty
from context.catalog.application.domain.model.table.table_property_catalogue import (
    TablePropertyCatalogue,
)
from context.catalog.application.domain.model.table.table_property_default_source import (
    TablePropertyDefaultSource,
)
from context.catalog.application.domain.model.table.table_property_definition import (
    TablePropertyDefinition,
)
from context.catalog.application.domain.model.table.table_property_not_resettable import (
    TablePropertyNotResettable,
)
from context.catalog.application.domain.model.table.table_property_reset import TablePropertyReset
from context.catalog.application.domain.model.table.table_summary import TableSummary

__all__ = [
    "DefaultPartitionFieldNames",
    "NullOrder",
    "PartitionChange",
    "PartitionField",
    "PartitionFieldComparison",
    "PartitionSpec",
    "PartitionSpecComparison",
    "PartitionTransform",
    "PartitionTransformKind",
    "SchemaChange",
    "SchemaComparison",
    "SchemaFieldComparison",
    "Snapshot",
    "SortDirection",
    "SortField",
    "SortOrder",
    "Table",
    "TableId",
    "TableProperty",
    "TablePropertyCatalogue",
    "TablePropertyDefaultSource",
    "TablePropertyDefinition",
    "TablePropertyNotResettable",
    "TablePropertyReset",
    "TableSummary",
    "iceberg_table_property_catalogue",
]
