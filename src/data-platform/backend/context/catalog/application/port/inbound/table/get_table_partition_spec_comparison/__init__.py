"""Compare one partition spec version of an Iceberg table with another."""

from context.catalog.application.port.inbound.table.get_table_partition_spec_comparison.input import (
    GetTablePartitionSpecComparisonUseCaseInput,
)
from context.catalog.application.port.inbound.table.get_table_partition_spec_comparison.output import (
    GetTablePartitionSpecComparisonUseCaseOutput,
)
from context.catalog.application.port.inbound.table.get_table_partition_spec_comparison.use_case import (
    GetTablePartitionSpecComparisonUseCase,
)

__all__ = [
    "GetTablePartitionSpecComparisonUseCase",
    "GetTablePartitionSpecComparisonUseCaseInput",
    "GetTablePartitionSpecComparisonUseCaseOutput",
]
