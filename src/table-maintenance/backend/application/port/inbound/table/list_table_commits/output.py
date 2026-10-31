"""Define the ListTableCommitsUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class ListTableCommitsUseCaseOutputItem:
    """One commit of the table."""

    snapshot_id: int
    parent_id: int | None
    committed_at: datetime
    operation: str | None
    writer: str
    added_records: int | None
    deleted_records: int | None
    added_data_files: int | None
    deleted_data_files: int | None
    added_delete_files: int | None
    removed_delete_files: int | None
    summary: dict[str, str]


@dataclass(frozen=True)
class ListTableCommitsUseCaseOutput:
    """Carry the commits, newest first, and whether more exist."""

    items: list[ListTableCommitsUseCaseOutputItem]
    truncated: bool
