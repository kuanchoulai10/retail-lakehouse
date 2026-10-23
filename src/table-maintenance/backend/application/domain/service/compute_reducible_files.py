"""Define the compute_reducible_files domain service."""

from __future__ import annotations

from application.domain.model.observation.partition_stats import PartitionStats


def compute_reducible_files(stats: PartitionStats, target_file_size_bytes: int) -> int:
    """Return how many files compaction could remove from a partition."""
    total = (
        stats.data_file_count
        + stats.position_delete_file_count
        + stats.equality_delete_file_count
    )
    expected = (
        -(-stats.total_data_file_size_bytes // target_file_size_bytes)
        if stats.total_data_file_size_bytes > 0
        else 0
    )
    return max(0, total - expected)
