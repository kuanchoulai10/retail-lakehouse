"""Build rewrite_data_files where clauses from selected Iceberg partitions."""

from __future__ import annotations

import math
import re
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import (
    PartitionFieldInfo,
    PartitionSpecInfo,
    PartitionStats,
    SpecFilter,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_EPOCH_YEAR = 1970
_PARAMETERIZED = re.compile(r"^(bucket|truncate)\[(\d+)\]$")
_DECIMAL = re.compile(r"^decimal\(\s*\d+\s*,\s*\d+\s*\)$")
_TIME_TRANSFORM_FUNCTIONS = {
    "year": "years",
    "month": "months",
    "day": "days",
    "hour": "hours",
}

_Value = str | int | float | bool | None


def build_partition_filters(
    catalog: str,
    specs: Sequence[PartitionSpecInfo],
    partitions: Sequence[PartitionStats],
) -> tuple[SpecFilter, ...]:
    """Return one where clause per spec id, sorted by spec id.

    An empty ``where`` means the whole table for that spec. Raises ``ValueError``
    for unknown spec ids or partition values that cannot be rendered.
    """
    specs_by_id = {spec.spec_id: spec for spec in specs}
    grouped: dict[int, list[PartitionStats]] = defaultdict(list)
    for partition in partitions:
        if partition.spec_id not in specs_by_id:
            raise ValueError(f"Unknown partition spec id {partition.spec_id}")
        grouped[partition.spec_id].append(partition)

    quoted_catalog = "`" + catalog.replace("`", "``") + "`"
    return tuple(
        SpecFilter(
            spec_id,
            _spec_where(quoted_catalog, specs_by_id[spec_id], grouped[spec_id]),
        )
        for spec_id in sorted(grouped)
    )


def _spec_where(catalog: str, spec: PartitionSpecInfo, partitions: Sequence[PartitionStats]) -> str:
    clauses: list[str] = []
    for partition in partitions:
        if len(partition.values) != len(spec.fields):
            raise ValueError(
                f"Partition has {len(partition.values)} values but spec {spec.spec_id} has {len(spec.fields)} fields"
            )
        terms: list[str] = []
        for field, value in zip(spec.fields, partition.values, strict=True):
            terms.extend(_field_terms(catalog, field, value))
        if not terms:
            return ""
        clauses.append("(" + " AND ".join(terms) + ")")
    return " OR ".join(sorted(set(clauses)))


def _field_terms(catalog: str, field: PartitionFieldInfo, value: _Value) -> list[str]:
    transform = field.transform
    if transform == "void":
        return []
    column = _quote_column(field.source_column)
    if transform == "identity" or transform in _TIME_TRANSFORM_FUNCTIONS:
        _reject_nanosecond(field)
    if value is None:
        return [f"{column} IS NULL"]
    if transform == "identity":
        return [f"{column} = {_literal(field.source_type, value)}"]
    if transform in _TIME_TRANSFORM_FUNCTIONS:
        return _time_terms(catalog, field, column, _as_int(value))
    match = _PARAMETERIZED.match(transform)
    if match is None:
        raise ValueError(f"Unsupported partition transform {transform!r}")
    kind, width = match.group(1), int(match.group(2))
    if kind == "bucket":
        return [f"{catalog}.system.bucket({width}, {column}) = {_as_int(value)}"]
    literal = _literal(field.source_type, value)
    return [f"{catalog}.system.truncate({width}, {column}) = {literal}"]


def _time_terms(catalog: str, field: PartitionFieldInfo, column: str, number: int) -> list[str]:
    transform = field.transform
    source_type = field.source_type
    if source_type == "date":
        if transform == "hour":
            raise ValueError("hour transform is not valid on a date column")
        start, end = _period_bounds(transform, number)
        render = _date_literal_from_datetime
    elif source_type in ("timestamp", "timestamptz"):
        start, end = _period_bounds(transform, number)

        def render(moment: datetime) -> str:
            return _timestamp_literal(source_type, moment)

    else:
        raise ValueError(f"Time transform {transform!r} on unsupported type {source_type!r}")

    function = f"{catalog}.system.{_TIME_TRANSFORM_FUNCTIONS[transform]}({column})"
    if transform == "day":
        equals = _date_literal_from_datetime(start)
    else:
        equals = str(number)
    return [
        f"{function} = {equals}",
        f"{column} >= {render(start)}",
        f"{column} < {render(end)}",
    ]


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


def _literal(source_type: str, value: _Value) -> str:
    if source_type in ("int", "long"):
        return str(_as_int(value))
    if source_type in ("float", "double"):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"Expected a number for {source_type}, got {value!r}")
        if not math.isfinite(value):
            raise ValueError(f"Non-finite {source_type} value {value!r}")
        return repr(float(value))
    if _DECIMAL.match(source_type):
        text = str(value)
        if not re.fullmatch(r"-?\d+(\.\d+)?", text):
            raise ValueError(f"Invalid decimal value {value!r}")
        return text
    if source_type == "string":
        if not isinstance(value, str):
            raise ValueError(f"Expected a string, got {value!r}")
        escaped = value.replace("\\", "\\\\").replace("'", "\\'")
        return f"'{escaped}'"
    if source_type == "boolean":
        if not isinstance(value, bool):
            raise ValueError(f"Expected a boolean, got {value!r}")
        return "true" if value else "false"
    if source_type == "date":
        return _date_literal_from_datetime(_EPOCH + timedelta(days=_as_int(value)))
    if source_type in ("timestamp", "timestamptz"):
        return _timestamp_literal(source_type, _EPOCH + timedelta(microseconds=_as_int(value)))
    raise ValueError(f"Unsupported partition source type {source_type!r}")


def _date_literal_from_datetime(moment: datetime) -> str:
    return f"DATE '{date(moment.year, moment.month, moment.day).isoformat()}'"


def _timestamp_literal(source_type: str, moment: datetime) -> str:
    text = moment.strftime("%Y-%m-%d %H:%M:%S.%f")
    if source_type == "timestamptz":
        return f"TIMESTAMP '{text}+00:00'"
    return f"TIMESTAMP_NTZ '{text}'"


def _as_int(value: _Value) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"Expected an integer partition value, got {value!r}")
    return value


def _reject_nanosecond(field: PartitionFieldInfo) -> None:
    if field.source_type.endswith("_ns"):
        raise ValueError(f"Nanosecond source type {field.source_type!r} is not supported for partition filters")


def _quote_column(column: str) -> str:
    return ".".join("`" + part.replace("`", "``") + "`" for part in column.split("."))
