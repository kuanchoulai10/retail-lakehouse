"""Provide the admission_lease_seconds function."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bootstrap.configs import AppSettings

_LEASE_PAST_DEADLINE_SECONDS = 15 * 60


def admission_lease_seconds(settings: AppSettings) -> int:
    """Return the admission lease the worker starts the admission workflow with.

    It outlives the configured attempt deadline by 15 minutes, so a slot is never
    taken from an attempt that is still within its deadline.
    """
    return settings.maintenance_attempt_deadline_seconds + _LEASE_PAST_DEADLINE_SECONDS
