"""Define the ListTagsService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from core.application.port.inbound.catalog.list_tags.input import ListTagsInput
from core.application.port.inbound.catalog.list_tags.output import (
    ListTagsOutput,
    ListTagsOutputItem,
)
from core.application.port.inbound.catalog.list_tags.use_case import ListTagsUseCase

if TYPE_CHECKING:
    from core.application.port.outbound.catalog.catalog_reader import CatalogReader


class ListTagsService(ListTagsUseCase):
    """List all tags by delegating to CatalogReader."""

    def __init__(self, reader: CatalogReader) -> None:
        """Initialize with the catalog reader port."""
        self._reader = reader

    def execute(self, request: ListTagsInput) -> ListTagsOutput:
        """Load table and return tags as output DTOs."""
        table = self._reader.load_table(request.namespace, request.table)
        return ListTagsOutput(
            tags=[
                ListTagsOutputItem(
                    name=t.name,
                    snapshot_id=t.snapshot_id,
                    max_ref_age_ms=t.max_ref_age_ms,
                )
                for t in table.tags
            ],
        )
