"""Test the reducible file count and the target file size resolution."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.shared import (
    PartitionStats,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    PartialProgress,
    RewriteDataFilesExecutionPolicy,
)
from context.table_maintenance.application.domain.service.shared import (
    resolve_execution_target_file_size,
    resolve_target_file_size,
)
from context.table_maintenance.application.domain.service.table import (
    compute_reducible_files,
)

MIB = 1024 * 1024
GIB = 1024 * MIB


def stats(data, pos, eq, size) -> PartitionStats:
    """Build partition stats with the given file counts and size."""
    return PartitionStats(
        spec_id=0,
        values=(),
        data_file_count=data,
        position_delete_file_count=pos,
        equality_delete_file_count=eq,
        total_data_file_size_bytes=size,
    )


def test_reducible_files_formula():
    """Reducible files count the files saved by compaction, delete files included."""
    assert compute_reducible_files(stats(20, 4, 0, GIB), 512 * MIB) == 22
    assert compute_reducible_files(stats(1, 0, 0, 2 * GIB), 512 * MIB) == 0
    assert compute_reducible_files(stats(0, 2, 1, 0), 512 * MIB) == 3


def test_target_file_size_resolution_order():
    """The measured target file size is the table property, then the default."""
    assert resolve_target_file_size({}) == 536870912
    assert resolve_target_file_size({"write.target-file-size-bytes": "1000"}) == 1000


def test_execution_target_file_size_resolution_order():
    """The executed target file size is the execution policy's value, then the table property, then the default."""
    props = {"write.target-file-size-bytes": "1000"}
    unset = RewriteDataFilesExecutionPolicy(min_input_files=2, partial_progress=PartialProgress(enabled=True))
    assert resolve_execution_target_file_size(unset, {}) == 536870912
    assert resolve_execution_target_file_size(unset, props) == 1000
    explicit = RewriteDataFilesExecutionPolicy(
        target_file_size_bytes=7, min_input_files=2, partial_progress=PartialProgress(enabled=True)
    )
    assert resolve_execution_target_file_size(explicit, props) == 7
