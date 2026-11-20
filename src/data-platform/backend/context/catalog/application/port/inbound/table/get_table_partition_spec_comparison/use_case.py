"""Define the GetTablePartitionSpecComparisonUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.catalog.application.port.inbound.table.get_table_partition_spec_comparison.input import (
    GetTablePartitionSpecComparisonUseCaseInput,
)
from context.catalog.application.port.inbound.table.get_table_partition_spec_comparison.output import (
    GetTablePartitionSpecComparisonUseCaseOutput,
)


class GetTablePartitionSpecComparisonUseCase(
    UseCase[GetTablePartitionSpecComparisonUseCaseInput, GetTablePartitionSpecComparisonUseCaseOutput]
):
    """Compare one partition spec version of an Iceberg table with another."""

    @abstractmethod
    def execute(
        self, request: GetTablePartitionSpecComparisonUseCaseInput
    ) -> GetTablePartitionSpecComparisonUseCaseOutput:
        """Compare one partition spec version of an Iceberg table with another."""
