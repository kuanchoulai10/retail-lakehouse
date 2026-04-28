"""Define the IsolationLevel enumeration."""

from enum import StrEnum


class IsolationLevel(StrEnum):
    """Iceberg write isolation level."""

    SERIALIZABLE = "serializable"
    SNAPSHOT = "snapshot"
