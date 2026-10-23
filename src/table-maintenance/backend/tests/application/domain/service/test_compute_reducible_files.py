from __future__ import annotations

from application.domain.model.maintenance_settings import RewriteDataFilesSettings
from application.domain.model.observation import PartitionStats
from application.domain.service.compute_reducible_files import compute_reducible_files
from application.domain.service.resolve_target_file_size import (
    resolve_target_file_size,
)

MIB = 1024 * 1024
GIB = 1024 * MIB


def stats(data, pos, eq, size) -> PartitionStats:
    return PartitionStats(0, (), data, pos, eq, size)


def test_reducible_files_formula():
    assert compute_reducible_files(stats(20, 4, 0, GIB), 512 * MIB) == 22
    assert compute_reducible_files(stats(1, 0, 0, 2 * GIB), 512 * MIB) == 0
    assert compute_reducible_files(stats(0, 2, 1, 0), 512 * MIB) == 3


def test_target_file_size_resolution_order():
    assert resolve_target_file_size(RewriteDataFilesSettings(), {}) == 536870912
    props = {"write.target-file-size-bytes": "1000"}
    assert resolve_target_file_size(RewriteDataFilesSettings(), props) == 1000
    explicit = RewriteDataFilesSettings(target_file_size_bytes=7)
    assert resolve_target_file_size(explicit, props) == 7
