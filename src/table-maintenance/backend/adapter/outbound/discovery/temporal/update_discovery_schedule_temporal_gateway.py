"""Define the UpdateDiscoveryScheduleTemporalGateway adapter."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from temporalio.client import RPCError
from temporalio.service import RPCStatusCode

from application.domain.model.maintenance.workflow_ids import DISCOVERY_SCHEDULE_ID
from application.port.outbound.discovery.update_discovery_schedule import (
    UpdateDiscoveryScheduleGateway,
)

if TYPE_CHECKING:
    from temporalio.client import Client

    from adapter.outbound.temporal.async_loop_bridge import AsyncLoopBridge
    from application.port.outbound.discovery.update_discovery_schedule import (
        UpdateDiscoveryScheduleGatewayInput,
    )

logger = logging.getLogger(__name__)


class UpdateDiscoveryScheduleTemporalGateway(UpdateDiscoveryScheduleGateway):
    """Pause or unpause the discovery schedule through Temporal."""

    def __init__(self, client: Client, bridge: AsyncLoopBridge) -> None:
        self._client = client
        self._bridge = bridge

    def update(self, input: UpdateDiscoveryScheduleGatewayInput) -> None:  # noqa: A002
        """Apply the paused flag, tolerating a schedule that does not exist yet."""
        self._bridge.run(lambda: self._update(input))

    async def _update(self, input: UpdateDiscoveryScheduleGatewayInput) -> None:  # noqa: A002
        handle = self._client.get_schedule_handle(DISCOVERY_SCHEDULE_ID)
        try:
            if input.paused:
                await handle.pause(note="paused by table-maintenance settings")
            else:
                await handle.unpause(note="resumed by table-maintenance settings")
        except RPCError as error:
            if error.status != RPCStatusCode.NOT_FOUND:
                raise
            logger.warning(
                "Discovery schedule %s does not exist yet; worker start will create it",
                DISCOVERY_SCHEDULE_ID,
            )
