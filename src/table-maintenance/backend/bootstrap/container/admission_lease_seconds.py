"""Define the admission lease the worker starts the admission workflow with."""

from __future__ import annotations

from adapter.hybrid.temporal.contracts.table_maintenance_admission import (
    DEFAULT_ADMISSION_LEASE_SECONDS,
)

ADMISSION_LEASE_SECONDS = DEFAULT_ADMISSION_LEASE_SECONDS
