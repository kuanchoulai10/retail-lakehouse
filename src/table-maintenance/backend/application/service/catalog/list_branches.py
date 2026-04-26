"""Define the ListBranchesService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.port.inbound.catalog.list_branches.input import ListBranchesInput
from application.port.inbound.catalog.list_branches.output import (
    ListBranchesOutput,
    ListBranchesOutputItem,
)
from application.port.inbound.catalog.list_branches.use_case import (
    ListBranchesUseCase,
)

if TYPE_CHECKING:
    from application.port.outbound.catalog.catalog_reader import CatalogReader


class ListBranchesService(ListBranchesUseCase):
    """List all branches by delegating to CatalogReader."""

    def __init__(self, reader: CatalogReader) -> None:
        """Initialize with the catalog reader port."""
        self._reader = reader

    def execute(self, request: ListBranchesInput) -> ListBranchesOutput:
        """Load table and return branches as output DTOs."""
        table = self._reader.load_table(request.namespace, request.table)
        return ListBranchesOutput(
            branches=[
                ListBranchesOutputItem(
                    name=b.id.value,
                    snapshot_id=b.snapshot_id,
                    max_snapshot_age_ms=b.retention.max_snapshot_age_ms
                    if b.retention
                    else None,
                    max_ref_age_ms=b.retention.max_ref_age_ms if b.retention else None,
                    min_snapshots_to_keep=b.retention.min_snapshots_to_keep
                    if b.retention
                    else None,
                )
                for b in table.branches
            ],
        )
