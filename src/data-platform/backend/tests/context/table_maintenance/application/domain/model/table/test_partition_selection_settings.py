"""Test the PartitionSelectionSettings value object."""

from __future__ import annotations

from datetime import timedelta

import pytest

from base import InvariantViolation
from context.table_maintenance.application.domain.model.table import (
    DEFAULT_PARTITION_SELECTION_SETTINGS,
    PartitionSelectionSettings,
)

SETTINGS = PartitionSelectionSettings.platform_default()


def test_platform_default_selection_settings():
    """The platform default is 10 partitions per job, a 2 minute quiet period and a 1 hour longest wait."""
    s = PartitionSelectionSettings.platform_default()
    assert (s.partitions_per_job, s.quiet_period, s.max_quiet_wait) == (10, timedelta(minutes=2), timedelta(hours=1))
    assert DEFAULT_PARTITION_SELECTION_SETTINGS == s


@pytest.mark.parametrize("n", [0, 1001])
def test_partitions_per_job_out_of_range_is_refused(n):
    """A cap below 1 or above 1000 is refused."""
    with pytest.raises(InvariantViolation, match="must be between 1 and 1000"):
        SETTINGS.with_changes(partitions_per_job=n)


@pytest.mark.parametrize("n", [1, 1000])
def test_partitions_per_job_bounds_are_accepted(n):
    """The cap bounds 1 and 1000 themselves are allowed."""
    assert SETTINGS.with_changes(partitions_per_job=n).partitions_per_job == n


def test_a_negative_quiet_period_is_refused():
    """A negative quiet period is refused."""
    with pytest.raises(InvariantViolation):
        SETTINGS.with_changes(quiet_period=timedelta(seconds=-1))


def test_a_negative_max_quiet_wait_is_refused():
    """A negative longest wait is refused."""
    with pytest.raises(InvariantViolation):
        SETTINGS.with_changes(max_quiet_wait=timedelta(seconds=-1))
