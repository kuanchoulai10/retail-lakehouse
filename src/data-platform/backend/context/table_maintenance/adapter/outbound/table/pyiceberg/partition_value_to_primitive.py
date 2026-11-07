"""Convert one PyIceberg partition value to its primitive internal form."""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import Any
from uuid import UUID

_EPOCH_DATE = date(1970, 1, 1)
_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_MICROS = 1_000_000


def partition_value_to_primitive(value: Any) -> str | int | float | bool | None:  # noqa: ANN401, PLR0911
    """Return the Iceberg internal representation of a partition value.

    Dates become int days, timestamps int micros, decimals and UUIDs strings,
    bytes hex strings. ``None`` stays ``None``.
    """
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, datetime):
        moment = value if value.tzinfo else value.replace(tzinfo=UTC)
        delta = moment - _EPOCH
        return (delta.days * 86_400 + delta.seconds) * _MICROS + delta.microseconds
    if isinstance(value, date):
        return (value - _EPOCH_DATE).days
    if isinstance(value, time):
        return (value.hour * 3600 + value.minute * 60 + value.second) * _MICROS + value.microsecond
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).hex()
    raise ValueError(f"Unsupported partition value {value!r}")
