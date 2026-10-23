"""Define the resolve_target_file_size domain service."""

from __future__ import annotations

from application.domain.model.maintenance_settings.rewrite_data_files_settings import (
    RewriteDataFilesSettings,
)

DEFAULT_TARGET_FILE_SIZE_BYTES = 536870912


def resolve_target_file_size(
    settings: RewriteDataFilesSettings, properties: dict[str, str]
) -> int:
    """Return the target size: settings, then table property, then 512 MiB."""
    if settings.target_file_size_bytes is not None:
        return settings.target_file_size_bytes
    value = properties.get("write.target-file-size-bytes")
    if value is not None:
        return int(value)
    return DEFAULT_TARGET_FILE_SIZE_BYTES
