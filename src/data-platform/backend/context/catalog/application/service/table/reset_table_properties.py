"""Define the ResetTablePropertiesService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.application.domain.model.table import TablePropertyNotResettable, iceberg_table_property_catalogue
from context.catalog.application.domain.service.table import (
    plan_table_property_reset,
    resolve_table_properties,
)
from context.catalog.application.exceptions import ConflictError, ValidationError
from context.catalog.application.port.inbound.table import (
    ResetTablePropertiesUseCase,
    ResetTablePropertiesUseCaseInput,
    ResetTablePropertiesUseCaseOutput,
)
from context.catalog.application.service.table.load_table_and_catalog import load_table_and_catalog
from context.catalog.application.service.table.table_id_from_parts import table_id_from_parts
from context.catalog.application.service.table.table_property_output_fields import (
    table_property_output_fields,
)

if TYPE_CHECKING:
    from context.catalog.application.port.outbound.catalog import CatalogsRepo
    from context.catalog.application.port.outbound.table import TablesRepo


class ResetTablePropertiesService(ResetTablePropertiesUseCase):
    """Reset properties of the table that was loaded to their defaults, never of one that replaced it."""

    def __init__(self, tables_repo: TablesRepo, catalogs_repo: CatalogsRepo) -> None:
        """Bind the repos: the table holds the values, its catalog the table defaults."""
        self._tables_repo = tables_repo
        self._catalogs_repo = catalogs_repo

    def execute(self, request: ResetTablePropertiesUseCaseInput) -> ResetTablePropertiesUseCaseOutput:
        """Plan the reset against the resolved defaults, then commit it through the property update.

        A key that is not resettable refuses the whole reset (ValidationError); a reset with
        nothing to change commits nothing; a changed table is a ConflictError asking to reload.
        """
        table_id = table_id_from_parts(request.catalog, request.namespace, request.name)
        if not request.expected_uuid.strip():
            raise ValidationError("expected_uuid must be the uuid of the table as it was loaded")
        if not request.keys:
            raise ValidationError("name at least one property to reset")
        conflict = ConflictError(f"table {request.name} changed since you loaded it, reload")
        table, catalog = load_table_and_catalog(self._tables_repo, self._catalogs_repo, table_id)
        if table.uuid != request.expected_uuid:
            raise conflict
        rows = resolve_table_properties(table, catalog, iceberg_table_property_catalogue())
        try:
            reset = plan_table_property_reset(rows, list(request.keys))
        except TablePropertyNotResettable as exc:
            raise ValidationError(str(exc)) from exc
        if not reset.is_empty:
            try:
                table = self._tables_repo.update_properties(
                    table_id, request.expected_uuid, dict(reset.updates), list(reset.removals)
                )
            except ConflictError as exc:
                raise conflict from exc
        fields = table_property_output_fields(table, catalog)
        return ResetTablePropertiesUseCaseOutput(
            uuid=fields["uuid"],
            iceberg_version=fields["iceberg_version"],
            items=tuple(ResetTablePropertiesUseCaseOutput.Property(**item) for item in fields["items"]),
        )
