"""Define the default admission lease, which outlives one attempt deadline."""

from __future__ import annotations

from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance import (
    DEFAULT_ATTEMPT_DEADLINE_SECONDS,
)

DEFAULT_ADMISSION_LEASE_SECONDS = DEFAULT_ATTEMPT_DEADLINE_SECONDS + 15 * 60
