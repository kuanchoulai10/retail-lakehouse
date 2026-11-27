"""Define the RecordingSyncDiscoverySchedulesGateway fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.port.outbound.table_discovery_policy import (
    SyncDiscoverySchedulesGateway,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from context.table_maintenance.application.port.outbound.table_discovery_policy import (
        SyncDiscoverySchedulesGatewayInput,
    )


class RecordingSyncDiscoverySchedulesGateway(SyncDiscoverySchedulesGateway):
    """Keep the scheduled catalogs in a set and record every sync.

    Set ``failing`` to make every sync raise; a failed sync is not recorded and changes nothing.
    """

    def __init__(self, scheduled: Iterable[str] = ()) -> None:
        """Start with the ``scheduled`` catalogs and no syncs."""
        self.scheduled: set[str] = set(scheduled)
        self.synced: list[SyncDiscoverySchedulesGatewayInput] = []
        self.failing = False

    def list_scheduled_catalogs(self) -> tuple[str, ...]:
        """Return the scheduled catalogs, sorted."""
        return tuple(sorted(self.scheduled))

    def sync(self, input: SyncDiscoverySchedulesGatewayInput) -> None:  # noqa: A002
        """Schedule ``input.catalogs``, unschedule ``input.removed`` and record the call."""
        if self.failing:
            msg = "temporal is down"
            raise RuntimeError(msg)
        self.scheduled = (self.scheduled | set(input.catalogs)) - set(input.removed)
        self.synced.append(input)
