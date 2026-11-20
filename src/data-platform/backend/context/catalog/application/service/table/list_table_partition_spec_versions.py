"""Define the ListTablePartitionSpecVersionsService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.application.domain.service.table import compare_partition_specs
from context.catalog.application.port.inbound.table import (
    ListTablePartitionSpecVersionsUseCase,
    ListTablePartitionSpecVersionsUseCaseInput,
    ListTablePartitionSpecVersionsUseCaseOutput,
)
from context.catalog.application.service.table.load_table import load_table
from context.catalog.application.service.table.table_id_from_parts import table_id_from_parts

if TYPE_CHECKING:
    from collections.abc import Mapping

    from context.catalog.application.port.outbound.table import PartitionSpec, Table, TablesRepo


def _version(
    table: Table, spec: PartitionSpec, column_paths: Mapping[int, tuple[str, ...]]
) -> ListTablePartitionSpecVersionsUseCaseOutput.Version:
    previous = table.previous_partition_spec(spec.spec_id)
    comparison = compare_partition_specs(previous, spec, column_paths)
    return ListTablePartitionSpecVersionsUseCaseOutput.Version(
        spec_id=spec.spec_id,
        previous_spec_id=None if previous is None else previous.spec_id,
        default=spec.spec_id == table.default_spec_id,
        field_count=comparison.field_count(),
        changes=None if previous is None else {str(kind): count for kind, count in comparison.change_counts().items()},
    )


class ListTablePartitionSpecVersionsService(ListTablePartitionSpecVersionsUseCase):
    """List every partition spec version of a table with what each changed against the version below it."""

    def __init__(self, tables_repo: TablesRepo) -> None:
        """Bind the repo."""
        self._tables_repo = tables_repo

    def execute(
        self, request: ListTablePartitionSpecVersionsUseCaseInput
    ) -> ListTablePartitionSpecVersionsUseCaseOutput:
        """Return the versions newest id first, or raise NotFoundError for an unknown table.

        The column paths are walked once for the table, not once per spec.
        """
        table = load_table(self._tables_repo, table_id_from_parts(request.catalog, request.namespace, request.name))
        column_paths = table.column_paths()
        return ListTablePartitionSpecVersionsUseCaseOutput(
            default_spec_id=table.default_spec_id,
            items=tuple(_version(table, spec, column_paths) for spec in reversed(table.partition_specs)),
        )
