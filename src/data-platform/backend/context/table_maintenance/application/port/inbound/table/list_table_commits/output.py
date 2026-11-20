"""Define the ListTableCommitsUseCaseOutput."""

from __future__ import annotations

from datetime import datetime

from base import UseCaseOutput


class ListTableCommitsUseCaseOutput(UseCaseOutput):
    """Carry the commits, newest first, and whether more exist."""

    class Commit(UseCaseOutput):
        """One commit of the table."""

        snapshot_id: int
        parent_id: int | None
        committed_at: datetime
        operation: str | None
        writer: str
        schema_id: int | None
        added_records: int | None
        deleted_records: int | None
        added_data_files: int | None
        deleted_data_files: int | None
        added_delete_files: int | None
        removed_delete_files: int | None
        summary: dict[str, str]

    items: tuple[Commit, ...]
    truncated: bool
