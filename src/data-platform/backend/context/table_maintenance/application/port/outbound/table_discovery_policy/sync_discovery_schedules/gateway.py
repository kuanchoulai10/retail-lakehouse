"""Define the SyncDiscoverySchedulesGateway outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base import Gateway

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table_discovery_policy.sync_discovery_schedules.input import (  # noqa: E501
        SyncDiscoverySchedulesGatewayInput,
    )


class SyncDiscoverySchedulesGateway(Gateway):
    """Keep the periodic discovery schedules, one per catalog discovery scans."""

    @abstractmethod
    def list_scheduled_catalogs(self) -> tuple[str, ...]:
        """Return the catalogs that have a discovery schedule, sorted.

        The listing may lag: a schedule created a moment ago can be missing from it, and one deleted a
        moment ago can still be in it.
        """

    @abstractmethod
    def sync(self, input: SyncDiscoverySchedulesGatewayInput) -> None:  # noqa: A002
        """Give each of ``input.catalogs`` a running schedule at the current interval; delete ``input.removed``'s.

        An existing schedule of ``input.catalogs`` is rewritten and unpaused. Removing a catalog that has
        no schedule does nothing, and the schedules of any other catalog are left alone.
        """
