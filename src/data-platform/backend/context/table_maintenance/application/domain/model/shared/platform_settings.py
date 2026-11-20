"""Define the PlatformSettings value object."""

from __future__ import annotations

from base import ValueObject
from context.table_maintenance.application.domain.model.shared.platform_compute_size import PlatformComputeSize


class PlatformSettings(ValueObject):
    """The platform-level settings the running component was started with, as people read them.

    Each field is one setting a person may want to look up: how long and how often
    a maintenance operation is attempted and how long an attempt may wait in its queue, the Spark
    size of each compute size, how far a failing operation's cooldown backs off,
    and how often discovery scans. Durations are in seconds. The composition root fills it from the
    settings it chose to show; nothing else about the deployment is here.
    """

    attempt_deadline_seconds: int
    max_attempts: int
    queue_wait_limit_seconds: int
    compute_sizes: tuple[PlatformComputeSize, ...]
    failure_backoff_cap_seconds: int
    discovery_interval_seconds: int
