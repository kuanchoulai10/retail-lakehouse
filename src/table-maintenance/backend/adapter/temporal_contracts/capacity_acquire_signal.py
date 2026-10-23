"""Define the CapacityAcquireSignal workflow contract."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CapacityAcquireSignal:
    """Payload of the acquire signal sent to the capacity limiter."""

    request_id: str
    requester_workflow_id: str
