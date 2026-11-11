"""Define the resolve_execution_target_file_size domain service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.service.shared.resolve_target_file_size import (
    resolve_target_file_size,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.table_maintenance_policy import (
        RewriteDataFilesExecutionPolicy,
    )


def resolve_execution_target_file_size(policy: RewriteDataFilesExecutionPolicy, properties: dict[str, str]) -> int:
    """Return the size compaction writes: the execution policy's, else the table property, else 512 MiB."""
    if policy.target_file_size_bytes is not None:
        return policy.target_file_size_bytes
    return resolve_target_file_size(properties)
