"""Define the CommitProperties value object."""

from __future__ import annotations

from dataclasses import dataclass

from base.value_object import ValueObject


@dataclass(frozen=True)
class CommitProperties(ValueObject):
    """Commit retry configuration properties."""

    num_retries: int | None = None
    retry_min_wait_ms: int | None = None
    retry_max_wait_ms: int | None = None
    total_retry_time_ms: int | None = None
