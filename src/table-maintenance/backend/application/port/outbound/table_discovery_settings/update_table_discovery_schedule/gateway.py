"""Define the UpdateTableDiscoveryScheduleGateway outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base.gateway import Gateway

if TYPE_CHECKING:
    from application.port.outbound.table_discovery_settings.update_table_discovery_schedule.input import (
        UpdateTableDiscoveryScheduleGatewayInput,
    )


class UpdateTableDiscoveryScheduleGateway(Gateway):
    """Pause or unpause the table discovery schedule."""

    @abstractmethod
    def update(self, input: UpdateTableDiscoveryScheduleGatewayInput) -> None:  # noqa: A002
        """Apply the paused flag to the schedule."""
