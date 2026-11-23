"""Define the partition_value_text function."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def partition_value_text(transform: str, source_type: str, value: str | float | bool | None) -> str | None:
    """Return a partition value as Iceberg prints it, or None for a null partition.

    A time transform shows its period (``2026``, ``2026-11``, ``2026-11-20``, ``2026-11-20-10``), an
    identity date or timestamp its day or instant, a boolean ``true`` or ``false``; anything else, and a
    value no calendar holds, is shown as it is stored.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if not isinstance(value, int):
        return str(value)
    try:
        return _time_text(transform, source_type, value) or str(value)
    except ValueError, OverflowError:
        return str(value)


def _time_text(transform: str, source_type: str, number: int) -> str | None:  # noqa: PLR0911
    if transform == "year":
        return f"{date(1970 + number, 1, 1).year:04d}"
    if transform == "month":
        year, month = divmod(number, 12)
        return f"{date(1970 + year, month + 1, 1):%Y-%m}"
    if transform == "day":
        return f"{_EPOCH + timedelta(days=number):%Y-%m-%d}"
    if transform == "hour":
        return f"{_EPOCH + timedelta(hours=number):%Y-%m-%d-%H}"
    if transform != "identity":
        return None
    if source_type == "date":
        return f"{_EPOCH + timedelta(days=number):%Y-%m-%d}"
    if source_type == "timestamptz":
        return (_EPOCH + timedelta(microseconds=number)).isoformat()
    if source_type == "timestamp":
        return (_EPOCH + timedelta(microseconds=number)).replace(tzinfo=None).isoformat()
    return None
