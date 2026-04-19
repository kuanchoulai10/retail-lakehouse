"""Define the supported Iceberg maintenance job types."""

from enum import StrEnum


class JobType(StrEnum):
    """Enumerate the available Iceberg table maintenance job types."""

    EXPIRE_SNAPSHOTS = "expire_snapshots"
    REMOVE_ORPHAN_FILES = "remove_orphan_files"
    REWRITE_DATA_FILES = "rewrite_data_files"
    REWRITE_MANIFESTS = "rewrite_manifests"
