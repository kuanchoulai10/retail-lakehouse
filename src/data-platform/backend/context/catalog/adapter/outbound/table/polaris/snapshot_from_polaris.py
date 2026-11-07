"""Define the snapshot_from_polaris function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.catalog.application.port.outbound.table import Snapshot

if TYPE_CHECKING:
    from collections.abc import Mapping

_OPERATION = "operation"


def snapshot_from_polaris(body: Mapping[str, Any]) -> Snapshot:
    """Map one Iceberg snapshot; the summary's ``operation`` becomes the operation, the rest the summary."""
    summary = {str(key): str(value) for key, value in (body.get("summary") or {}).items()}
    operation = summary.pop(_OPERATION, None)
    parent = body.get("parent-snapshot-id")
    return Snapshot(
        snapshot_id=int(body["snapshot-id"]),
        parent_id=None if parent is None else int(parent),
        timestamp_ms=int(body["timestamp-ms"]),
        operation=operation,
        summary=summary,
    )
