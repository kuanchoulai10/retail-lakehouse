"""Define the table_from_polaris function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.catalog.adapter.outbound.shared.polaris import (
    polaris_integer,
    polaris_text,
    polaris_text_map,
    read_polaris_reply,
)
from context.catalog.adapter.outbound.table.polaris.partition_spec_from_polaris import (
    partition_spec_from_polaris,
)
from context.catalog.adapter.outbound.table.polaris.snapshot_from_polaris import snapshot_from_polaris
from context.catalog.adapter.outbound.table.polaris.sort_order_from_polaris import sort_order_from_polaris
from context.catalog.adapter.outbound.table.polaris.table_schema_from_polaris import (
    table_schema_from_polaris,
)
from context.catalog.application.port.outbound.table import Snapshot, Table

if TYPE_CHECKING:
    from collections.abc import Mapping

    import httpx

    from context.catalog.application.port.outbound.table import TableId

_NO_SNAPSHOT = -1


def _current_snapshot_id(value: object) -> int | None:
    if value is None:
        return None
    current = polaris_integer(value, "current-snapshot-id")
    return None if current == _NO_SNAPSHOT else current


def _snapshots(value: Any) -> list[Snapshot]:  # noqa: ANN401
    if value is None:
        return []
    if not isinstance(value, list):
        raise TypeError(f"snapshots must be a list, not {value!r}")
    return [snapshot_from_polaris(snapshot) for snapshot in value]


def _table(table_id: TableId, metadata: Mapping[str, Any]) -> Table:
    return Table(
        id=table_id,
        uuid=polaris_text(metadata["table-uuid"], "table-uuid"),
        format_version=polaris_integer(metadata["format-version"], "format-version"),
        location=polaris_text(metadata["location"], "location"),
        current_snapshot_id=_current_snapshot_id(metadata.get("current-snapshot-id")),
        last_updated_ms=polaris_integer(metadata["last-updated-ms"], "last-updated-ms"),
        current_schema=table_schema_from_polaris(metadata),
        partition_spec=partition_spec_from_polaris(metadata),
        sort_order=sort_order_from_polaris(metadata),
        snapshots=_snapshots(metadata.get("snapshots")),
        properties=polaris_text_map(metadata.get("properties"), "properties"),
    )


def table_from_polaris(table_id: TableId, response: httpx.Response) -> Table:
    """Map the ``metadata`` of a LoadTableResult or CommitTableResponse reply to a Table.

    v1's -1 snapshot id means none, and missing or null snapshots or properties are none.
    Nothing is coerced: a value of the wrong type (a bool where an integer belongs, a number
    where text belongs) is refused. A reply that is not JSON, has no ``metadata``, or holds
    metadata this backend cannot read raises CatalogUnavailableError naming the table, so the
    API answers 502 rather than 500.
    """
    return read_polaris_reply(response, f"table {table_id.name}", lambda body: _table(table_id, body["metadata"]))
