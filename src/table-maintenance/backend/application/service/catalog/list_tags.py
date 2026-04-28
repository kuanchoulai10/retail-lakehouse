"""Define the ListTagsService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.port.inbound.catalog.list_tags.input import ListTagsUseCaseInput
from application.port.inbound.catalog.list_tags.output import (
    ListTagsUseCaseOutput,
    ListTagsUseCaseOutputItem,
)
from application.port.inbound.catalog.list_tags.use_case import ListTagsUseCase

if TYPE_CHECKING:
    from application.port.outbound.catalog.read_catalog.gateway import (
        ReadCatalogGateway,
    )


class ListTagsService(ListTagsUseCase):
    """List all tags by delegating to ReadCatalogGateway."""

    def __init__(self, reader: ReadCatalogGateway) -> None:
        """Initialize with the catalog reader port."""
        self._reader = reader

    def execute(self, request: ListTagsUseCaseInput) -> ListTagsUseCaseOutput:
        """Load table and return tags as output DTOs."""
        table = self._reader.load_table(request.namespace, request.table)
        return ListTagsUseCaseOutput(
            tags=[
                ListTagsUseCaseOutputItem(
                    name=t.name,
                    snapshot_id=t.snapshot_id,
                    max_ref_age_ms=t.max_ref_age_ms,
                )
                for t in table.tags
            ],
        )
