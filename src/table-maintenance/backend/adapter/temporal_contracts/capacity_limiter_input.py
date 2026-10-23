"""Define the CapacityLimiterInput workflow contract."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CapacityLimiterInput:
    """Carry the capacity limit, lease, holders and queue across continue-as-new.

    ``holders`` maps a request id to ``{"requester_workflow_id", "granted_at"}`` with
    ``granted_at`` an ISO-8601 string; ``queue`` holds FIFO entries
    ``{"request_id", "requester_workflow_id"}``.
    """

    limit: int
    lease_seconds: int = 21600
    holders: dict[str, dict] = field(default_factory=dict)
    queue: list[dict] = field(default_factory=list)
