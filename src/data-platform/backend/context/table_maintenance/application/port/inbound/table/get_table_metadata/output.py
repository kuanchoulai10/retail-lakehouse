"""Define the GetTableMetadataUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from typing import Any


@dataclass(frozen=True)
class GetTableMetadataUseCaseOutput:
    """Describe the catalog definition and current totals of a table."""

    uuid: str
    format_version: int
    location: str
    properties: dict[str, str]
    schema_fields: list[dict[str, Any]]
    specs: list[dict[str, Any]]
    current_snapshot_id: int | None
    snapshot_count: int
    last_committed_at: datetime | None
    total_records: int | None
    total_data_files: int | None
    total_delete_files: int | None
    total_files_size_bytes: int | None
