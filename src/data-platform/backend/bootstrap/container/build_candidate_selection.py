"""Provide the build_candidate_selection function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.compaction_candidate import (
    CandidateFilters,
    CandidateScoring,
    CandidateSelection,
)

if TYPE_CHECKING:
    from bootstrap.configs import CompactionSettings


def build_candidate_selection(settings: CompactionSettings) -> CandidateSelection:
    """Return how compaction candidates are filtered, scored and picked, as the settings say.

    A setting the selection refuses (a weight below zero, an S bound above the M
    bound) fails here, when the component starts, not on the first plan.
    """
    return CandidateSelection(
        partitions_per_run=settings.partitions_per_run,
        scoring=CandidateScoring(
            benefit_weight=settings.benefit_weight,
            cost_weight=settings.cost_weight,
            benefit_reference_files=settings.benefit_reference_files,
            cost_reference_gb_hours=settings.cost_reference_gb_hours,
        ),
        filters=CandidateFilters(
            min_partition_bytes=settings.min_partition_bytes,
            quiet_seconds=settings.quiet_seconds,
            max_quiet_wait_seconds=settings.max_quiet_wait_seconds,
        ),
        default_throughput_bytes_per_hour=float(settings.default_throughput_bytes_per_hour),
        size_s_max_bytes=settings.size_s_max_bytes,
        size_m_max_bytes=settings.size_m_max_bytes,
    )
