"""Define the partition_label domain service."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from context.table_maintenance.application.domain.model.compaction_candidate import PartitionKey
    from context.table_maintenance.application.domain.model.shared import PartitionFieldInfo, PartitionSpecInfo

WHOLE_TABLE_LABEL = "whole table"
_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_EPOCH_YEAR = 1970
_Value = str | int | float | bool | None


def partition_label(specs: Sequence[PartitionSpecInfo], partition: PartitionKey) -> str:
    """Name a partition for people: ``field=value`` pairs of its spec, values as they are written.

    Time transforms read as calendar values (a day as ``2025-10-01``, a month as
    ``2025-10``), dropped (void) fields are left out, the whole-table key reads
    ``whole table``, and a spec the table no longer lists falls back to its raw values.
    """
    if partition.is_whole_table:
        return WHOLE_TABLE_LABEL
    spec = next((s for s in specs if s.spec_id == partition.spec_id), None)
    if spec is None or len(spec.fields) != len(partition.values):
        return f"spec {partition.spec_id}: " + ", ".join(_plain(v) for v in partition.values)
    pairs = [
        f"{field.name}={_text(field, value)}"
        for field, value in zip(spec.fields, partition.values, strict=True)
        if field.transform != "void"
    ]
    return ", ".join(pairs) if pairs else WHOLE_TABLE_LABEL


def _text(field: PartitionFieldInfo, value: _Value) -> str:  # noqa: PLR0911
    if value is None or isinstance(value, bool) or not isinstance(value, int):
        return _plain(value)
    try:
        match field.transform:
            case "year":
                return f"{_EPOCH_YEAR + value:04d}"
            case "month":
                year, month = divmod(value, 12)
                return f"{_EPOCH_YEAR + year:04d}-{month + 1:02d}"
            case "day":
                return (_EPOCH + timedelta(days=value)).date().isoformat()
            case "hour":
                return (_EPOCH + timedelta(hours=value)).strftime("%Y-%m-%d-%H")
            case "identity" if field.source_type == "date":
                return (date(1970, 1, 1) + timedelta(days=value)).isoformat()
            case "identity" if field.source_type in ("timestamp", "timestamptz"):
                return (_EPOCH + timedelta(microseconds=value)).replace(tzinfo=None).isoformat()
    except OverflowError:
        return _plain(value)
    return _plain(value)


def _plain(value: _Value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)
