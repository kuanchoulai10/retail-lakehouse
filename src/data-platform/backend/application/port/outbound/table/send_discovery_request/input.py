"""Define the SendDiscoveryRequestGatewayInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SendDiscoveryRequestGatewayInput:
    """Name the catalog, and optionally the namespace, to discover tables in."""

    catalog: str
    namespace: str | None
