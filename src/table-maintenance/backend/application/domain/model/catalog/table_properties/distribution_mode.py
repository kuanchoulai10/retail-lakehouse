"""Define the DistributionMode enumeration."""

from enum import StrEnum


class DistributionMode(StrEnum):
    """Iceberg write distribution mode."""

    NONE = "none"
    HASH = "hash"
    RANGE = "range"
