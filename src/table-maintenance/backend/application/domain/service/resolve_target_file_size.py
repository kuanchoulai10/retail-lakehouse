"""Define the resolve_target_file_size domain service."""

from __future__ import annotations

from application.domain.model.maintenance_settings.rewrite_data_files_settings import (
    RewriteDataFilesSettings,
)

from application.domain.service.positive_int_property import positive_int_property

DEFAULT_TARGET_FILE_SIZE_BYTES = 536870912


def resolve_target_file_size(
    settings: RewriteDataFilesSettings, properties: dict[str, str]
) -> int:
    """Return the target size: settings, then table property, then 512 MiB."""
    if settings.target_file_size_bytes is not None:
        return settings.target_file_size_bytes
    value = positive_int_property(properties, "write.target-file-size-bytes")
    return value if value is not None else DEFAULT_TARGET_FILE_SIZE_BYTES
