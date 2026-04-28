"""Define the WriteMode enumeration."""

from enum import StrEnum


class WriteMode(StrEnum):
    """Iceberg write operation mode."""

    COPY_ON_WRITE = "copy-on-write"
    MERGE_ON_READ = "merge-on-read"
