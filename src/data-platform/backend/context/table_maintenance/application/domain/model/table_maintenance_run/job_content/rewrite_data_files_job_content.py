"""Define the RewriteDataFilesJobContent value object."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, PositiveInt, model_validator

from base import ValueObject
from context.table_maintenance.application.domain.model.shared import MaintenanceOperation, SpecPartitions
from context.table_maintenance.application.domain.model.table_maintenance_policy import RewriteDataFilesOptions


class RewriteDataFilesJobContent(ValueObject):
    """Describe what one compaction does: the file size it writes, its options and the partitions it rewrites.

    ``target_file_size_bytes`` is the table's ``write.target-file-size-bytes`` (or Iceberg's default),
    ``options`` are the policy's, and empty ``partitions`` means the whole table; otherwise one entry
    per partition spec, sorted by spec id.
    """

    operation: Literal[MaintenanceOperation.REWRITE_DATA_FILES] = MaintenanceOperation.REWRITE_DATA_FILES
    target_file_size_bytes: PositiveInt
    options: RewriteDataFilesOptions = Field(default_factory=RewriteDataFilesOptions)
    partitions: tuple[SpecPartitions, ...] = ()

    @model_validator(mode="after")
    def _one_selection_per_spec_in_order(self) -> RewriteDataFilesJobContent:
        spec_ids = [selection.spec.spec_id for selection in self.partitions]
        for spec_id in spec_ids:
            if spec_ids.count(spec_id) > 1:
                raise ValueError(f"spec {spec_id} is selected twice")
        if spec_ids != sorted(spec_ids):
            raise ValueError("the partition selections are sorted by spec id")
        return self
