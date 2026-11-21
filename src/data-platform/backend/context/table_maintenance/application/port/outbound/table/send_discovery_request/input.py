"""Define the SendDiscoveryRequestGatewayInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SendDiscoveryRequestGatewayInput:
    """Name the catalog, and optionally the namespace, to discover tables in.

    ``change_id`` is set when the request follows a change of the discovery policies or their
    attachments: each change has its own id and gets its own run, so it never joins a run that read
    older settings. Without it the request is an ad hoc one, folded into any ad hoc run of the same
    scope that is still going.
    """

    catalog: str
    namespace: str | None
    change_id: str | None = None
