"""Define the TableMaintenanceAdmissionInput workflow contract."""

from __future__ import annotations

from dataclasses import dataclass, field

from adapter.temporal_contracts.default_admission_lease_seconds import (
    DEFAULT_ADMISSION_LEASE_SECONDS,
)


@dataclass(frozen=True)
class TableMaintenanceAdmissionInput:
    """Carry the admission limit, lease, holders and queue across continue-as-new.

    The lease defaults to the attempt deadline plus 15 minutes, so a slot is never
    taken from an attempt that is still within its deadline.

    ``holders`` maps a request id to ``{"requester_workflow_id", "granted_at"}`` with
    ``granted_at`` an ISO-8601 string; ``queue`` holds FIFO entries
    ``{"request_id", "requester_workflow_id"}``.
    """

    limit: int
    lease_seconds: int = DEFAULT_ADMISSION_LEASE_SECONDS
    holders: dict[str, dict] = field(default_factory=dict)
    queue: list[dict] = field(default_factory=list)
