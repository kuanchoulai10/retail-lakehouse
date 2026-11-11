"""Define the resolve_target_file_size domain service."""

from __future__ import annotations

from context.table_maintenance.application.domain.service.shared.positive_int_property import (
    positive_int_property,
)

DEFAULT_TARGET_FILE_SIZE_BYTES = 536870912
TARGET_FILE_SIZE_PROPERTY = "write.target-file-size-bytes"


def resolve_target_file_size(properties: dict[str, str]) -> int:
    """Return the table's own target file size: its property, else 512 MiB."""
    value = positive_int_property(properties, TARGET_FILE_SIZE_PROPERTY)
    return value if value is not None else DEFAULT_TARGET_FILE_SIZE_BYTES
