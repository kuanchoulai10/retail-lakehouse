"""Define the PartitionTransformKind enum."""

from __future__ import annotations

from enum import StrEnum


class PartitionTransformKind(StrEnum):
    """One kind of Iceberg partition transform, or ``unknown`` for one this backend does not know."""

    IDENTITY = "identity"
    YEAR = "year"
    MONTH = "month"
    DAY = "day"
    HOUR = "hour"
    BUCKET = "bucket"
    TRUNCATE = "truncate"
    VOID = "void"
    UNKNOWN = "unknown"
