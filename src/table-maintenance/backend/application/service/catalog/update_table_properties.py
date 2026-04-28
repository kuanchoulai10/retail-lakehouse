"""Define the UpdateTablePropertiesService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.port.inbound.catalog.update_table_properties.input import (
    UpdateTablePropertiesUseCaseInput,
)
from application.port.inbound.catalog.update_table_properties.output import (
    UpdateTablePropertiesUseCaseOutput,
)
from application.port.inbound.catalog.update_table_properties.use_case import (
    UpdateTablePropertiesUseCase,
)
from application.port.outbound.catalog.update_table_properties.input import (
    UpdateTablePropertiesGatewayInput,
)
from application.service.catalog.table_properties_serializer import (
    table_properties_to_dict,
)

if TYPE_CHECKING:
    from application.port.outbound.catalog.read_catalog.gateway import (
        ReadCatalogGateway,
    )
    from application.port.outbound.catalog.update_table_properties.gateway import (
        UpdateTablePropertiesGateway,
    )


class UpdateTablePropertiesService(UpdateTablePropertiesUseCase):
    """Update table properties by delegating to the catalog gateway."""

    def __init__(
        self,
        writer: UpdateTablePropertiesGateway,
        reader: ReadCatalogGateway,
    ) -> None:
        """Initialize with writer and reader gateways."""
        self._writer = writer
        self._reader = reader

    def execute(
        self, request: UpdateTablePropertiesUseCaseInput
    ) -> UpdateTablePropertiesUseCaseOutput:
        """Split properties into updates/removals, apply, and return updated state."""
        updates: dict[str, str] = {}
        removals: list[str] = []

        for key, value in request.properties.items():
            if value is None:
                removals.append(key)
            else:
                updates[key] = value

        self._writer.execute(
            UpdateTablePropertiesGatewayInput(
                namespace=request.namespace,
                table=request.table,
                updates=updates,
                removals=removals,
            )
        )

        table = self._reader.load_table(request.namespace, request.table)
        return UpdateTablePropertiesUseCaseOutput(
            properties=table_properties_to_dict(table.properties),
        )
