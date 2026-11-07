"""Define the GetTableUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


@dataclass(frozen=True)
class GetTableUseCaseOutput:
    """Describe the table, every field primitive.

    ``schema`` is ``{schema_id, fields: [{id, name, type, required, doc}]}`` with ``type`` as
    text; ``partition_spec`` is ``{spec_id, fields: [{source_id, field_id, name, transform}]}``;
    ``sort_order`` is ``{order_id, fields: [{source_id, transform, direction, null_order}]}``;
    each snapshot is ``{id, parent_id, timestamp_ms, operation, summary}``; ``summary`` holds
    ``total_records``, ``total_data_files`` and ``total_files_size`` of the current snapshot,
    each None when it is not reported.
    """

    catalog: str
    namespace: list[str]
    name: str
    uuid: str
    format_version: int
    location: str
    current_snapshot_id: int | None
    last_updated_ms: int
    schema: dict[str, Any]
    partition_spec: dict[str, Any]
    sort_order: dict[str, Any]
    snapshots: list[dict[str, Any]]
    properties: dict[str, str]
    summary: dict[str, int | None]
