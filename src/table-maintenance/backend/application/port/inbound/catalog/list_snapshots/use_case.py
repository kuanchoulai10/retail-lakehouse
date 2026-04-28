"""Define the ListSnapshotsUseCase interface."""

from __future__ import annotations

from base.use_case import UseCase
from application.port.inbound.catalog.list_snapshots.input import (
    ListSnapshotsUseCaseInput,
)
from application.port.inbound.catalog.list_snapshots.output import (
    ListSnapshotsUseCaseOutput,
)


class ListSnapshotsUseCase(
    UseCase[ListSnapshotsUseCaseInput, ListSnapshotsUseCaseOutput]
):
    """List all snapshots for a table."""
