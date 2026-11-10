"""Define the snapshot_from_polaris function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.catalog.adapter.outbound.shared.polaris import polaris_integer, polaris_text_map
from context.catalog.application.port.outbound.table import Snapshot

if TYPE_CHECKING:
    from collections.abc import Mapping

_OPERATION = "operation"


def snapshot_from_polaris(body: Mapping[str, Any]) -> Snapshot:
    """Map one Iceberg snapshot; the summary's ``operation`` becomes the operation, the rest the summary.

    A missing or null summary or parent is none. Nothing is coerced: an id or timestamp that is
    not an integer (a bool is not one), or a summary that is not an object of text values,
    raises TypeError.
    """
    summary = polaris_text_map(body.get("summary"), "snapshot summary")
    operation = summary.pop(_OPERATION, None)
    parent = body.get("parent-snapshot-id")
    return Snapshot(
        snapshot_id=polaris_integer(body["snapshot-id"], "snapshot-id"),
        parent_id=None if parent is None else polaris_integer(parent, "parent-snapshot-id"),
        timestamp_ms=polaris_integer(body["timestamp-ms"], "timestamp-ms"),
        operation=operation,
        summary=summary,
    )
