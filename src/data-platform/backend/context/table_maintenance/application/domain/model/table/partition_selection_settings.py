"""Define the PartitionSelectionSettings value object."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from pydantic import field_validator

from base import ValueObject
from context.table_maintenance.application.domain.model.shared import NonNegativeDuration

if TYPE_CHECKING:
    from typing import Self

_MAX_PARTITIONS_PER_JOB = 1000


class PartitionSelectionSettings(ValueObject):
    """Hold how a scheduled compaction chooses the partitions of one job.

    ``partitions_per_job`` caps the partitions one job compacts. A partition written less than
    ``quiet_period`` ago waits for a later check, until it has been over its target for
    ``max_quiet_wait``. A partition over its target for ``max_quiet_wait`` also goes first under
    the cap, oldest first, so none waits behind the cap for ever. A zero ``quiet_period`` or
    ``max_quiet_wait`` means nothing waits; with a zero ``max_quiet_wait`` every partition counts
    as past it, so the cap takes the oldest first.
    """

    partitions_per_job: int
    quiet_period: NonNegativeDuration
    max_quiet_wait: NonNegativeDuration

    @field_validator("partitions_per_job")
    @classmethod
    def _within_bounds(cls, value: int) -> int:
        if not 1 <= value <= _MAX_PARTITIONS_PER_JOB:
            raise ValueError(f"must be between 1 and {_MAX_PARTITIONS_PER_JOB}")
        return value

    @classmethod
    def platform_default(cls) -> Self:
        """Return the settings a platform runs with unless it is told otherwise."""
        return cls(
            partitions_per_job=10,
            quiet_period=timedelta(seconds=120),
            max_quiet_wait=timedelta(hours=1),
        )
