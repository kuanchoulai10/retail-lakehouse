"""Define the SendDiscoveryRequestGatewayInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SendDiscoveryRequestGatewayInput:
    """Name the catalog, and optionally the namespace, to discover tables in.

    A catalog has one scan at a time: a request for the whole catalog starts it, or asks the scan
    already going (the periodic one or another request's) to scan once more when it finishes, so
    the catalog is scanned again after the request in every case. ``change_id`` is set when the
    request follows a change of the discovery policies; a namespace request with one gets its own
    run per change, so it never joins a run that read older settings. Without it a namespace
    request is an ad hoc one, folded into any ad hoc run of the same namespace that is still going.
    """

    catalog: str
    namespace: str | None
    change_id: str | None = None
