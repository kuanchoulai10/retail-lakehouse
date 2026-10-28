"""Define the default admission lease, which outlives one attempt deadline."""

from __future__ import annotations

from adapter.hybrid.temporal.contracts.default_attempt_deadline_seconds import (
    DEFAULT_ATTEMPT_DEADLINE_SECONDS,
)

DEFAULT_ADMISSION_LEASE_SECONDS = DEFAULT_ATTEMPT_DEADLINE_SECONDS + 15 * 60
