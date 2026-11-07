"""Define the StorageType enumeration."""

from __future__ import annotations

from enum import StrEnum


class StorageType(StrEnum):
    """Name the kind of storage a catalog keeps its data in."""

    S3 = "S3"
    AZURE = "AZURE"
    GCS = "GCS"
    FILE = "FILE"
