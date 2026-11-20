"""Define the CreateTableUseCaseOutput."""

from __future__ import annotations

from typing import Any

from base import UseCaseOutput


class CreateTableUseCaseOutput(UseCaseOutput):
    """Describe the table, every field primitive.

    ``table_schema`` is ``{schema_id, fields: [{id, name, type, required, doc}]}`` with ``type`` as
    text; ``partition_spec`` is ``{spec_id, fields: [{source_id, field_id, name, transform}]}``;
    ``sort_order`` is ``{order_id, fields: [{source_id, transform, direction, null_order}]}``;
    each snapshot is ``{id, parent_id, timestamp_ms, schema_id, operation, summary}``, with
    ``schema_id`` None when the table does not record it; ``summary`` holds ``total_records``,
    ``total_data_files`` and ``total_files_size`` of the current snapshot, each None when it is
    not reported.
    """

    catalog: str
    namespace: tuple[str, ...]
    name: str
    uuid: str
    format_version: int
    location: str
    current_snapshot_id: int | None
    last_updated_ms: int
    table_schema: dict[str, Any]
    partition_spec: dict[str, Any]
    sort_order: dict[str, Any]
    snapshots: tuple[dict[str, Any], ...]
    properties: dict[str, str]
    summary: dict[str, int | None]
