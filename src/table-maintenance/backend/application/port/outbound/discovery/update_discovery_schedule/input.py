"""Define the UpdateDiscoveryScheduleGatewayInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UpdateDiscoveryScheduleGatewayInput:
    """Carry the desired paused state of the discovery schedule."""

    paused: bool
