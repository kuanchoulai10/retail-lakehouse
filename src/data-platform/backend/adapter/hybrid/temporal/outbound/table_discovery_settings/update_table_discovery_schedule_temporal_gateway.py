"""Define the UpdateTableDiscoveryScheduleTemporalGateway adapter."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from temporalio.client import RPCError
from temporalio.service import RPCStatusCode

from adapter.hybrid.temporal.contracts.table_discovery import (
    TABLE_DISCOVERY_SCHEDULE_ID_PREFIX,
)
from application.port.outbound.table_discovery_settings import (
    UpdateTableDiscoveryScheduleGateway,
)

if TYPE_CHECKING:
    from temporalio.client import Client

    from adapter.hybrid.temporal.outbound.shared import AsyncLoopBridge
    from application.port.outbound.table_discovery_settings import (
        UpdateTableDiscoveryScheduleGatewayInput,
    )

logger = logging.getLogger(__name__)

_SCHEDULE_ID_PREFIX = TABLE_DISCOVERY_SCHEDULE_ID_PREFIX


class UpdateTableDiscoveryScheduleTemporalGateway(UpdateTableDiscoveryScheduleGateway):
    """Pause or unpause every per-catalog discovery schedule through Temporal."""

    def __init__(self, client: Client, bridge: AsyncLoopBridge) -> None:
        self._client = client
        self._bridge = bridge

    def update(self, input: UpdateTableDiscoveryScheduleGatewayInput) -> None:  # noqa: A002
        """Apply the paused flag, tolerating schedules that do not exist yet."""
        self._bridge.run(lambda: self._update(input))

    async def _update(self, input: UpdateTableDiscoveryScheduleGatewayInput) -> None:  # noqa: A002
        schedule_ids = [
            schedule.id
            async for schedule in await self._client.list_schedules()
            if schedule.id.startswith(_SCHEDULE_ID_PREFIX)
        ]
        if not schedule_ids:
            logger.warning(
                "No discovery schedule (%s*) exists yet; worker start will create it",
                _SCHEDULE_ID_PREFIX,
            )
        for schedule_id in schedule_ids:
            await self._apply(schedule_id, paused=input.paused)

    async def _apply(self, schedule_id: str, *, paused: bool) -> None:
        handle = self._client.get_schedule_handle(schedule_id)
        try:
            if paused:
                await handle.pause(note="paused by table-maintenance settings")
            else:
                await handle.unpause(note="resumed by table-maintenance settings")
        except RPCError as error:
            if error.status != RPCStatusCode.NOT_FOUND:
                raise
            logger.warning("Discovery schedule %s vanished; skipping it", schedule_id)
