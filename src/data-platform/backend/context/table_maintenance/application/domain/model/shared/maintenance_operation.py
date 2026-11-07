"""Define the MaintenanceOperation enumeration."""

from __future__ import annotations

from enum import StrEnum


class MaintenanceOperation(StrEnum):
    """Enumerate the Iceberg maintenance operations a table can undergo."""

    REWRITE_DATA_FILES = "rewrite_data_files"
    REWRITE_MANIFESTS = "rewrite_manifests"
    EXPIRE_SNAPSHOTS = "expire_snapshots"
    REMOVE_ORPHAN_FILES = "remove_orphan_files"

    @classmethod
    def ordered(cls) -> tuple[MaintenanceOperation, ...]:
        """Return the operations in execution order."""
        return (
            cls.REWRITE_DATA_FILES,
            cls.REWRITE_MANIFESTS,
            cls.EXPIRE_SNAPSHOTS,
            cls.REMOVE_ORPHAN_FILES,
        )
