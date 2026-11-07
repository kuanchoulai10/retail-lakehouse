"""Define the CreateGenericTableService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.application.exceptions import ValidationError
from context.catalog.application.port.inbound.generic_table import (
    CreateGenericTableUseCase,
    CreateGenericTableUseCaseInput,
    CreateGenericTableUseCaseOutput,
)
from context.catalog.application.port.outbound.generic_table import GenericTable
from context.catalog.application.service.generic_table.generic_table_id_from_parts import (
    generic_table_id_from_parts,
)
from context.catalog.application.service.generic_table.generic_table_output_fields import (
    generic_table_output_fields,
)

if TYPE_CHECKING:
    from context.catalog.application.port.outbound.generic_table import GenericTablesRepo


def _text_or_none(value: str | None) -> str | None:
    return value.strip() if value and value.strip() else None


class CreateGenericTableService(CreateGenericTableUseCase):
    """Create a generic table from the create generic table form."""

    def __init__(self, generic_tables_repo: GenericTablesRepo) -> None:
        """Bind the repo."""
        self._generic_tables_repo = generic_tables_repo

    def execute(self, request: CreateGenericTableUseCaseInput) -> CreateGenericTableUseCaseOutput:
        """Validate the form, create the generic table and return it as the catalog saved it."""
        table_id = generic_table_id_from_parts(request.catalog, request.namespace, request.name)
        if not request.format.strip():
            raise ValidationError("a generic table needs a format")
        table = GenericTable(
            id=table_id,
            format=request.format.strip(),
            base_location=_text_or_none(request.base_location),
            doc=_text_or_none(request.doc),
            properties=dict(request.properties),
        )
        return CreateGenericTableUseCaseOutput(**generic_table_output_fields(self._generic_tables_repo.create(table)))
