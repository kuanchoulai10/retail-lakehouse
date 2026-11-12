"""Provide the admission_lease_seconds function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance_admission import (
    ADMISSION_LEASE_MARGIN_SECONDS,
)

if TYPE_CHECKING:
    from bootstrap.configs import AppSettings


def admission_lease_seconds(settings: AppSettings) -> int:
    """Return the admission lease the worker starts the admission workflow with.

    It outlives the configured attempt deadline by 15 minutes, so a slot is never
    taken from an attempt that is still within its deadline. It applies only to
    acquire requests without a lease of their own; every maintenance attempt
    sends one.
    """
    return settings.maintenance_attempt_deadline_seconds + ADMISSION_LEASE_MARGIN_SECONDS
