"""Define the UpdateTablePropertiesService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.application.exceptions import ConflictError, ValidationError
from context.catalog.application.port.inbound.table import (
    UpdateTablePropertiesUseCase,
    UpdateTablePropertiesUseCaseInput,
    UpdateTablePropertiesUseCaseOutput,
)
from context.catalog.application.service.table.table_id_from_parts import table_id_from_parts
from context.catalog.application.service.table.table_output_fields import table_output_fields

if TYPE_CHECKING:
    from context.catalog.application.port.outbound.table import TablesRepo


class UpdateTablePropertiesService(UpdateTablePropertiesUseCase):
    """Set and remove properties of the table that was loaded, never of one that replaced it."""

    def __init__(self, tables_repo: TablesRepo) -> None:
        """Bind the repo."""
        self._tables_repo = tables_repo

    def execute(self, request: UpdateTablePropertiesUseCaseInput) -> UpdateTablePropertiesUseCaseOutput:
        """Refuse a key both set and removed, then save; a changed table is a ConflictError asking to reload."""
        table_id = table_id_from_parts(request.catalog, request.namespace, request.name)
        if not request.expected_uuid.strip():
            raise ValidationError("expected_uuid must be the uuid of the table as it was loaded")
        both = sorted(set(request.updates) & set(request.removals))
        if both:
            raise ValidationError(f"properties cannot be both updated and removed: {', '.join(both)}")
        try:
            saved = self._tables_repo.update_properties(
                table_id, request.expected_uuid, dict(request.updates), list(request.removals)
            )
        except ConflictError as exc:
            raise ConflictError(f"table {request.name} changed since you loaded it, reload") from exc
        return UpdateTablePropertiesUseCaseOutput(**table_output_fields(saved))
