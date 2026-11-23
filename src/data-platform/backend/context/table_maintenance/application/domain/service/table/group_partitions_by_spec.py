"""Group the partitions selected for compaction by their partition spec."""

from __future__ import annotations

import math
import re
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import (
    PartitionFieldInfo,
    PartitionSpecInfo,
    PartitionStats,
    SpecPartitions,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_EPOCH_YEAR = 1970
_PARAMETERIZED = re.compile(r"^(bucket|truncate)\[(\d+)\]$")
_DECIMAL = re.compile(r"^decimal\(\s*\d+\s*,\s*\d+\s*\)$")
_TIME_TRANSFORMS = frozenset({"year", "month", "day", "hour"})

_Value = str | int | float | bool | None


def group_partitions_by_spec(
    specs: Sequence[PartitionSpecInfo],
    partitions: Sequence[PartitionStats],
) -> tuple[SpecPartitions, ...]:
    """Return the selected partitions grouped per spec, sorted by spec id, or ``()`` for the whole table.

    Every value is checked against its field, so a compaction is only scoped to partitions a
    maintenance call can name. A partition of a spec with nothing to filter on (no field, or only
    ``void`` fields) means the whole table. Raises ``ValueError`` for an unknown spec id, a value count
    that does not match the spec, and a value, transform or column type a partition filter cannot
    express.
    """
    specs_by_id = {spec.spec_id: spec for spec in specs}
    grouped: dict[int, list[tuple[_Value, ...]]] = defaultdict(list)
    for partition in partitions:
        spec = specs_by_id.get(partition.spec_id)
        if spec is None:
            raise ValueError(f"Unknown partition spec id {partition.spec_id}")
        _check_partition(spec, partition.values)
        grouped[spec.spec_id].append(partition.values)
    if any(specs_by_id[spec_id].is_unpartitioned for spec_id in grouped):
        return ()
    return tuple(
        SpecPartitions(spec=specs_by_id[spec_id], values=tuple(grouped[spec_id])) for spec_id in sorted(grouped)
    )


def _check_partition(spec: PartitionSpecInfo, values: tuple[_Value, ...]) -> None:
    if len(values) != len(spec.fields):
        raise ValueError(f"Partition has {len(values)} values but spec {spec.spec_id} has {len(spec.fields)} fields")
    for field, value in zip(spec.fields, values, strict=True):
        _check_field(field, value)


def _check_field(field: PartitionFieldInfo, value: _Value) -> None:
    transform = field.transform
    if transform == "void":
        return
    if (transform == "identity" or transform in _TIME_TRANSFORMS) and field.source_type.endswith("_ns"):
        raise ValueError(f"Nanosecond source type {field.source_type!r} is not supported for partition filters")
    if value is None:
        return
    if transform == "identity":
        _check_literal(field.source_type, value)
        return
    if transform in _TIME_TRANSFORMS:
        _check_period(field, _as_int(value))
        return
    match = _PARAMETERIZED.match(transform)
    if match is None:
        raise ValueError(f"Unsupported partition transform {transform!r}")
    if match.group(1) == "bucket":
        _as_int(value)
    else:
        _check_literal(field.source_type, value)


def _check_period(field: PartitionFieldInfo, number: int) -> None:
    if field.source_type == "date":
        if field.transform == "hour":
            raise ValueError("hour transform is not valid on a date column")
    elif field.source_type not in ("timestamp", "timestamptz"):
        raise ValueError(f"Time transform {field.transform!r} on unsupported type {field.source_type!r}")
    _period_bounds(field.transform, number)


def _period_bounds(transform: str, number: int) -> tuple[datetime, datetime]:
    try:
        if transform == "year":
            return (
                datetime(_EPOCH_YEAR + number, 1, 1, tzinfo=UTC),
                datetime(_EPOCH_YEAR + number + 1, 1, 1, tzinfo=UTC),
            )
        if transform == "month":
            year, month = divmod(number, 12)
            start = datetime(_EPOCH_YEAR + year, month + 1, 1, tzinfo=UTC)
            end = (
                datetime(start.year + 1, 1, 1, tzinfo=UTC)
                if start.month == 12
                else datetime(start.year, start.month + 1, 1, tzinfo=UTC)
            )
            return start, end
        if transform == "day":
            start = _EPOCH + timedelta(days=number)
            return start, start + timedelta(days=1)
        start = _EPOCH + timedelta(hours=number)
        return start, start + timedelta(hours=1)
    except (ValueError, OverflowError) as error:
        raise ValueError(f"{transform} value {number} is out of range") from error


def _check_literal(source_type: str, value: _Value) -> None:  # noqa: C901
    if source_type in ("int", "long"):
        _as_int(value)
    elif source_type in ("float", "double"):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"Expected a number for {source_type}, got {value!r}")
        if not math.isfinite(value):
            raise ValueError(f"Non-finite {source_type} value {value!r}")
    elif _DECIMAL.match(source_type):
        if not re.fullmatch(r"-?\d+(\.\d+)?", str(value)):
            raise ValueError(f"Invalid decimal value {value!r}")
    elif source_type == "string":
        if not isinstance(value, str):
            raise ValueError(f"Expected a string, got {value!r}")
    elif source_type == "boolean":
        if not isinstance(value, bool):
            raise ValueError(f"Expected a boolean, got {value!r}")
    elif source_type == "date":
        _instant(source_type, _as_int(value), "days")
    elif source_type in ("timestamp", "timestamptz"):
        _instant(source_type, _as_int(value), "microseconds")
    else:
        raise ValueError(f"Unsupported partition source type {source_type!r}")


def _instant(source_type: str, number: int, unit: str) -> datetime:
    try:
        return _EPOCH + timedelta(**{unit: number})
    except (ValueError, OverflowError) as error:
        raise ValueError(f"{source_type} value {number} is out of range") from error


def _as_int(value: _Value) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"Expected an integer partition value, got {value!r}")
    return value
