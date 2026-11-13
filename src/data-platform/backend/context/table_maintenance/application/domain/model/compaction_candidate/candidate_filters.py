"""Define the CandidateFilters value object."""

from __future__ import annotations

from datetime import timedelta

from pydantic import NonNegativeInt

from base import ValueObject


class CandidateFilters(ValueObject):
    """Say which qualifying partitions are held back for now.

    A partition with less data than ``min_partition_bytes`` is too small to be
    worth a compaction. A partition written within the last ``quiet_seconds`` is
    still being written, so compacting it now would soon be undone; it is held
    until the writes pause for that long, but never longer than
    ``max_quiet_wait_seconds`` in a row, so a partition written without pause is
    still compacted.
    """

    min_partition_bytes: NonNegativeInt = 0
    quiet_seconds: NonNegativeInt = 120
    max_quiet_wait_seconds: NonNegativeInt = 3600

    @property
    def quiet_period(self) -> timedelta:
        """Return how long writes must pause before a partition counts as quiet."""
        return timedelta(seconds=self.quiet_seconds)

    @property
    def max_quiet_wait(self) -> timedelta:
        """Return the longest a partition waits in a row for its writes to pause."""
        return timedelta(seconds=self.max_quiet_wait_seconds)
