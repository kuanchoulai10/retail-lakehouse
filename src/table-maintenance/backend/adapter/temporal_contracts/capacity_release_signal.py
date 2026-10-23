"""Define the CapacityReleaseSignal workflow contract."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CapacityReleaseSignal:
    """Payload of the release signal sent to the capacity limiter."""

    request_id: str
