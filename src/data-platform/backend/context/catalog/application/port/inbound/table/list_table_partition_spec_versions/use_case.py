"""Define the ListTablePartitionSpecVersionsUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.catalog.application.port.inbound.table.list_table_partition_spec_versions.input import (
    ListTablePartitionSpecVersionsUseCaseInput,
)
from context.catalog.application.port.inbound.table.list_table_partition_spec_versions.output import (
    ListTablePartitionSpecVersionsUseCaseOutput,
)


class ListTablePartitionSpecVersionsUseCase(
    UseCase[ListTablePartitionSpecVersionsUseCaseInput, ListTablePartitionSpecVersionsUseCaseOutput]
):
    """List every partition spec version of an Iceberg table, newest id first, with what each changed."""

    @abstractmethod
    def execute(
        self, request: ListTablePartitionSpecVersionsUseCaseInput
    ) -> ListTablePartitionSpecVersionsUseCaseOutput:
        """List every partition spec version of an Iceberg table, newest id first, with what each changed."""
