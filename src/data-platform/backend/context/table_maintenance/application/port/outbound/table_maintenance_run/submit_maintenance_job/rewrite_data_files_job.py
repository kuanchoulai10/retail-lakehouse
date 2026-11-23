"""Define the RewriteDataFilesJob."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table_maintenance_run.submit_maintenance_job.job_partition_spec import (  # noqa: E501
        JobPartitionSpec,
    )


@dataclass(frozen=True)
class RewriteDataFilesJob:
    """Describe a compaction: the file size it writes, the partitions it rewrites and its options.

    Empty ``partitions`` means the whole table. An option left ``None`` is the procedure's default.
    """

    target_file_size_bytes: int
    partitions: tuple[JobPartitionSpec, ...] = ()
    strategy: str | None = None
    sort_order: str | None = None
    min_input_files: int | None = None
    partial_progress_enabled: bool | None = None
    partial_progress_max_commits: int | None = None
    max_concurrent_file_group_rewrites: int | None = None
    rewrite_all: bool | None = None
    delete_file_threshold: int | None = None
    remove_dangling_deletes: bool | None = None
    max_file_group_size_bytes: int | None = None
