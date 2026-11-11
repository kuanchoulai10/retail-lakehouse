"""Define the SendDiscoveryRequestGatewayInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SendDiscoveryRequestGatewayInput:
    """Name the catalog, and optionally the namespace, to discover tables in.

    ``rules_version`` is set when the request follows a save of the discovery
    rules: it is the saved version, and each saved version gets its own run.
    Without it the request is an ad hoc one, folded into any ad hoc run of the
    same scope that is still going.
    """

    catalog: str
    namespace: str | None
    rules_version: int | None = None
