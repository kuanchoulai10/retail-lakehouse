"""Define the TableMetadata."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TableMetadata:
    """A table located in the catalog, with its Iceberg table-uuid.

    ``last_committed_at`` is the ISO-8601 commit time of the table's newest
    snapshot, or None when it has none.
    """

    catalog: str
    namespace: str
    table: str
    table_uuid: str
    last_committed_at: str | None = None
