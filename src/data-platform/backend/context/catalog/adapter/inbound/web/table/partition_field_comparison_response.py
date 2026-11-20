"""Define the partition_field_comparison_response function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.adapter.inbound.web.table.dto import PartitionFieldComparisonApiResponse

if TYPE_CHECKING:
    from context.catalog.application.port.inbound.table import GetTablePartitionSpecComparisonUseCaseOutput


def _expression(transform: str | None, source_id: int | None, source_path: tuple[str, ...] | None) -> str | None:
    """Write Iceberg's ``transform(column)`` text; a column no schema holds is ``#<id>``, an absent side None."""
    if transform is None:
        return None
    source = f"#{source_id}" if source_path is None else ".".join(source_path)
    return f"{transform}({source})"


def partition_field_comparison_response(
    field: GetTablePartitionSpecComparisonUseCaseOutput.Field,
) -> PartitionFieldComparisonApiResponse:
    """Map one compared partition field to its response, writing each side's ``transform(column)`` text."""
    return PartitionFieldComparisonApiResponse.model_validate(
        {
            "field_id": field.field_id,
            "previous_field_id": field.previous_field_id,
            "name": field.name,
            "previous_name": field.previous_name,
            "source_path": field.source_path,
            "previous_source_path": field.previous_source_path,
            "transform": field.transform,
            "previous_transform": field.previous_transform,
            "changes": field.changes,
            "expression": _expression(field.transform, field.source_id, field.source_path),
            "previous_expression": _expression(
                field.previous_transform, field.previous_source_id, field.previous_source_path
            ),
        }
    )
