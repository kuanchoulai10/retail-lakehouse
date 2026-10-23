"""Define the SendDiscoveryRequestGatewayInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SendDiscoveryRequestGatewayInput:
    """Carry the arguments to send a discovery request to the workflow."""

    catalog: str
    namespace: str | None
