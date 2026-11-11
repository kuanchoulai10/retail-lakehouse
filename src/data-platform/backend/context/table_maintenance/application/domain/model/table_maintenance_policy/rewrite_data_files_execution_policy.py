"""Define the RewriteDataFilesExecutionPolicy value object."""

from __future__ import annotations

from pydantic import PositiveInt

from base import ValueObject
from context.table_maintenance.application.domain.model.table_maintenance_policy.partial_progress import PartialProgress


class RewriteDataFilesExecutionPolicy(ValueObject):
    """Configure how small data files are compacted."""

    target_file_size_bytes: PositiveInt | None = None
    min_input_files: PositiveInt
    partial_progress: PartialProgress
