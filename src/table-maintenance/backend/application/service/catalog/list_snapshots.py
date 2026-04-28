"""Define the ListSnapshotsService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.port.inbound.catalog.list_snapshots.input import (
    ListSnapshotsUseCaseInput,
)
from application.port.inbound.catalog.list_snapshots.output import (
    ListSnapshotsUseCaseOutput,
    ListSnapshotsUseCaseOutputItem,
)
from application.port.inbound.catalog.list_snapshots.use_case import (
    ListSnapshotsUseCase,
)

if TYPE_CHECKING:
    from application.port.outbound.catalog.read_catalog.gateway import (
        ReadCatalogGateway,
    )


class ListSnapshotsService(ListSnapshotsUseCase):
    """List all snapshots by delegating to ReadCatalogGateway."""

    def __init__(self, reader: ReadCatalogGateway) -> None:
        """Initialize with the catalog reader port."""
        self._reader = reader

    def execute(self, request: ListSnapshotsUseCaseInput) -> ListSnapshotsUseCaseOutput:
        """Load table and return snapshots as output DTOs."""
        table = self._reader.load_table(request.namespace, request.table)
        return ListSnapshotsUseCaseOutput(
            snapshots=[
                ListSnapshotsUseCaseOutputItem(
                    snapshot_id=s.snapshot_id,
                    parent_id=s.parent_id,
                    timestamp_ms=s.timestamp_ms,
                    summary=s.summary.data,
                )
                for s in table.snapshots
            ],
        )
