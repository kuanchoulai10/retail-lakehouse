"""Define the GetTablePartitionSpecComparisonService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.application.domain.service.table import compare_partition_specs
from context.catalog.application.exceptions import NotFoundError
from context.catalog.application.port.inbound.table import (
    GetTablePartitionSpecComparisonUseCase,
    GetTablePartitionSpecComparisonUseCaseInput,
    GetTablePartitionSpecComparisonUseCaseOutput,
)
from context.catalog.application.service.table.load_table import load_table
from context.catalog.application.service.table.table_id_from_parts import table_id_from_parts

if TYPE_CHECKING:
    from context.catalog.application.port.outbound.table import PartitionSpec, Table, TablesRepo


def _spec(table: Table, spec_id: int) -> PartitionSpec:
    spec = table.partition_spec_by_id(spec_id)
    if spec is None:
        raise NotFoundError(f"partition spec {spec_id} not found in table {table.id.name}")
    return spec


class GetTablePartitionSpecComparisonService(GetTablePartitionSpecComparisonUseCase):
    """Compare a partition spec version of a table with another."""

    def __init__(self, tables_repo: TablesRepo) -> None:
        """Bind the repo."""
        self._tables_repo = tables_repo

    def execute(
        self, request: GetTablePartitionSpecComparisonUseCaseInput
    ) -> GetTablePartitionSpecComparisonUseCaseOutput:
        """Return every field of the spec against the chosen base, else the previous version.

        Raises NotFoundError for an unknown table, spec or base. The first version has no base.
        """
        table = load_table(self._tables_repo, table_id_from_parts(request.catalog, request.namespace, request.name))
        spec = _spec(table, request.spec_id)
        base = table.previous_partition_spec(spec.spec_id)
        if request.base_spec_id is not None:
            base = _spec(table, request.base_spec_id)
        comparison = compare_partition_specs(base, spec, table.column_paths())
        return GetTablePartitionSpecComparisonUseCaseOutput(
            base_spec_id=comparison.base_spec_id,
            spec_id=comparison.spec_id,
            items=tuple(
                GetTablePartitionSpecComparisonUseCaseOutput.Field(
                    field_id=field.field_id,
                    previous_field_id=field.previous_field_id,
                    name=field.name,
                    previous_name=field.previous_name,
                    source_path=field.source_path,
                    previous_source_path=field.previous_source_path,
                    transform=field.transform,
                    previous_transform=field.previous_transform,
                    changes=tuple(str(change) for change in field.changes),
                    expression=field.expression(),
                    previous_expression=field.previous_expression(),
                )
                for field in comparison.fields
            ),
        )
