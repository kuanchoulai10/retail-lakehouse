"""Test the reducible file count and the target file size resolution."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.shared import (
    PartitionStats,
    RewriteDataFilesSettings,
)
from context.table_maintenance.application.domain.service.shared import (
    resolve_target_file_size,
)
from context.table_maintenance.application.domain.service.table import (
    compute_reducible_files,
)

MIB = 1024 * 1024
GIB = 1024 * MIB


def stats(data, pos, eq, size) -> PartitionStats:
    """Build partition stats with the given file counts and size."""
    return PartitionStats(0, (), data, pos, eq, size)


def test_reducible_files_formula():
    """Reducible files count the files saved by compaction, delete files included."""
    assert compute_reducible_files(stats(20, 4, 0, GIB), 512 * MIB) == 22
    assert compute_reducible_files(stats(1, 0, 0, 2 * GIB), 512 * MIB) == 0
    assert compute_reducible_files(stats(0, 2, 1, 0), 512 * MIB) == 3


def test_target_file_size_resolution_order():
    """The target file size is the explicit setting, then the table property, then the default."""
    assert resolve_target_file_size(RewriteDataFilesSettings(), {}) == 536870912
    props = {"write.target-file-size-bytes": "1000"}
    assert resolve_target_file_size(RewriteDataFilesSettings(), props) == 1000
    explicit = RewriteDataFilesSettings(target_file_size_bytes=7)
    assert resolve_target_file_size(explicit, props) == 7
