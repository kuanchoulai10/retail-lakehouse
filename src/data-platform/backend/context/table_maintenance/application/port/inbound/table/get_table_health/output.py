"""Define the GetTableHealthUseCaseOutput."""

from __future__ import annotations

from datetime import datetime

from base import UseCaseOutput


class GetTableHealthUseCaseOutput(UseCaseOutput):
    """Describe the maintenance evaluation of a table and its delete files."""

    class Operation(UseCaseOutput):
        """Describe the scheduler's verdict on one maintenance operation."""

        operation: str
        verdict: str
        measured: int | None
        threshold: int | None
        next_eligible_at: datetime | None
        qualifying_partitions: int | None
        size_bytes: int | None
        size_source: str | None

    scheduled: bool
    not_scheduled_reason: str | None
    operations: tuple[Operation, ...]
    position_delete_files: int
    equality_delete_files: int
