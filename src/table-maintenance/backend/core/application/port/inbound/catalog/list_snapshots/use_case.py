"""Define the ListSnapshotsUseCase interface."""

from __future__ import annotations

from core.base.use_case import UseCase
from core.application.port.inbound.catalog.list_snapshots.input import (
    ListSnapshotsInput,
)
from core.application.port.inbound.catalog.list_snapshots.output import (
    ListSnapshotsOutput,
)


class ListSnapshotsUseCase(UseCase[ListSnapshotsInput, ListSnapshotsOutput]):
    """List all snapshots for a table."""
