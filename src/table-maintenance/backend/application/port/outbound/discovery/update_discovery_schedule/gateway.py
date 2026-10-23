"""Define the UpdateDiscoveryScheduleGateway outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base.gateway import Gateway

if TYPE_CHECKING:
    from application.port.outbound.discovery.update_discovery_schedule.input import (
        UpdateDiscoveryScheduleGatewayInput,
    )


class UpdateDiscoveryScheduleGateway(Gateway):
    """Pause or unpause the table discovery schedule."""

    @abstractmethod
    def update(self, input: UpdateDiscoveryScheduleGatewayInput) -> None:  # noqa: A002
        """Apply the paused flag to the schedule."""
