"""Test the compaction candidate selection built from the compaction settings."""

from __future__ import annotations

import pytest

from bootstrap.configs import CompactionSettings
from bootstrap.container import build_candidate_selection
from context.table_maintenance.application.domain.model.compaction_candidate import (
    CandidateFilters,
    CandidateScoring,
    CandidateSelection,
)


def test_default_settings_give_the_default_selection():
    """The default settings select, score and filter as the domain's defaults do."""
    assert build_candidate_selection(CompactionSettings()) == CandidateSelection()


def test_every_setting_reaches_the_selection():
    """Each setting lands on its place in the selection, its scoring or its filters."""
    selection = build_candidate_selection(
        CompactionSettings(
            partitions_per_run=4,
            min_partition_bytes=1024,
            quiet_seconds=30,
            max_quiet_wait_seconds=900,
            benefit_weight=0.6,
            cost_weight=0.4,
            benefit_reference_files=50,
            cost_reference_gb_hours=2.0,
            default_throughput_bytes_per_hour=1024**3,
            size_s_max_bytes=128 * 1024**2,
            size_m_max_bytes=512 * 1024**2,
        )
    )

    assert selection == CandidateSelection(
        partitions_per_run=4,
        scoring=CandidateScoring(
            benefit_weight=0.6, cost_weight=0.4, benefit_reference_files=50, cost_reference_gb_hours=2.0
        ),
        filters=CandidateFilters(min_partition_bytes=1024, quiet_seconds=30, max_quiet_wait_seconds=900),
        default_throughput_bytes_per_hour=float(1024**3),
        size_s_max_bytes=128 * 1024**2,
        size_m_max_bytes=512 * 1024**2,
    )


def test_a_setting_the_selection_refuses_fails_at_startup():
    """An S bound above the M bound is refused when the selection is built, not on the first plan."""
    with pytest.raises(ValueError, match="S bound"):
        build_candidate_selection(CompactionSettings(size_s_max_bytes=2 * 1024**3))
