"""Define the GetTableService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.port.inbound.catalog.get_table.input import GetTableUseCaseInput
from application.port.inbound.catalog.get_table.output import (
    GetTableUseCaseOutput,
    GetTableSchemaFieldUseCaseOutput,
    GetTableSchemaUseCaseOutput,
)
from application.port.inbound.catalog.get_table.use_case import GetTableUseCase

if TYPE_CHECKING:
    from application.port.outbound.catalog.read_catalog.gateway import (
        ReadCatalogGateway,
    )


class GetTableService(GetTableUseCase):
    """Get table metadata by delegating to ReadCatalogGateway."""

    def __init__(self, reader: ReadCatalogGateway) -> None:
        """Initialize with the catalog reader port."""
        self._reader = reader

    def execute(self, request: GetTableUseCaseInput) -> GetTableUseCaseOutput:
        """Load table and return metadata as output DTO."""
        table = self._reader.load_table(request.namespace, request.table)
        return GetTableUseCaseOutput(
            name=table.name,
            namespace=table.namespace,
            location=table.location,
            current_snapshot_id=table.current_snapshot_id,
            schema=GetTableSchemaUseCaseOutput(
                fields=[
                    GetTableSchemaFieldUseCaseOutput(
                        field_id=f.field_id,
                        name=f.name,
                        field_type=f.field_type,
                        required=f.required,
                    )
                    for f in table.schema.fields
                ],
            ),
            properties=table.properties,
        )
