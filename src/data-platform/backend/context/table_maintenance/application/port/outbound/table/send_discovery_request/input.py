"""Define the SendDiscoveryRequestGatewayInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SendDiscoveryRequestGatewayInput:
    """Name the catalog, and optionally the namespace, to discover tables in.

    ``change_id`` is set when the request follows a change of the discovery policies or their
    attachments: each change has its own id and gets its own run, so it never joins a run that read
    older settings. Without it the request is an ad hoc one, folded into any ad hoc run of the same
    scope that is still going. ``retires_schedule`` marks the final scan the worker start gives a
    catalog it stops scanning, which also has its own run under ``change_id``.
    """

    catalog: str
    namespace: str | None
    change_id: str | None = None
    retires_schedule: bool = False

    def __post_init__(self) -> None:
        """Refuse a final scan of a retired schedule that has no change id."""
        if self.retires_schedule and self.change_id is None:
            msg = "a final scan of a retired schedule needs a change id"
            raise ValueError(msg)
