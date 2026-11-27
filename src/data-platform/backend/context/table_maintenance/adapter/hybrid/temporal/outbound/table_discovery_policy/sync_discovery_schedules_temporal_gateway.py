"""Define the SyncDiscoverySchedulesTemporalGateway adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING

from temporalio.client import RPCError, RPCStatusCode, ScheduleAlreadyRunningError, ScheduleUpdate

from context.table_maintenance.adapter.hybrid.temporal.contracts.table_discovery import (
    TABLE_DISCOVERY_SCHEDULE_ID_PREFIX,
    table_discovery_schedule_id,
)
from context.table_maintenance.adapter.hybrid.temporal.outbound.table_discovery_policy.table_discovery_schedule import (  # noqa: E501
    table_discovery_schedule,
)
from context.table_maintenance.application.port.outbound.table_discovery_policy import (
    SyncDiscoverySchedulesGateway,
)

if TYPE_CHECKING:
    from datetime import timedelta

    from temporalio.client import Client, Schedule, ScheduleUpdateInput

    from context.table_maintenance.adapter.hybrid.temporal.outbound.shared import (
        AsyncLoopBridge,
    )
    from context.table_maintenance.application.port.outbound.table_discovery_policy import (
        SyncDiscoverySchedulesGatewayInput,
    )


class SyncDiscoverySchedulesTemporalGateway(SyncDiscoverySchedulesGateway):
    """Keep one Temporal schedule ``table-discovery:catalog={catalog}`` per scanned catalog."""

    def __init__(self, client: Client, bridge: AsyncLoopBridge, *, interval: timedelta) -> None:
        """Keep the client, the bridge that runs its async calls and the interval every schedule fires at."""
        self._client = client
        self._bridge = bridge
        self._interval = interval

    def list_scheduled_catalogs(self) -> tuple[str, ...]:
        """Return the catalogs of the schedules whose id starts with the discovery prefix, sorted.

        Temporal lists schedules from its eventually consistent visibility store, so the listing can
        lag behind a create or a delete.
        """
        return self._bridge.run(self._list)

    def sync(self, input: SyncDiscoverySchedulesGatewayInput) -> None:  # noqa: A002
        """Create or rewrite and unpause each wanted schedule, then delete each removed one.

        Reads no listing: each create falls back to an update when the schedule exists, and a delete of
        a schedule already gone is ignored.
        """
        self._bridge.run(lambda: self._sync(input))

    async def _list(self) -> tuple[str, ...]:
        catalogs = [
            s.id.removeprefix(TABLE_DISCOVERY_SCHEDULE_ID_PREFIX)
            async for s in await self._client.list_schedules()
            if s.id.startswith(TABLE_DISCOVERY_SCHEDULE_ID_PREFIX)
        ]
        return tuple(sorted(catalogs))

    async def _sync(self, input: SyncDiscoverySchedulesGatewayInput) -> None:  # noqa: A002
        for catalog in input.catalogs:
            await self._ensure(catalog)
        for catalog in input.removed:
            await self._delete(catalog)

    async def _ensure(self, catalog: str) -> None:
        schedule_id = table_discovery_schedule_id(catalog)
        schedule = table_discovery_schedule(catalog, interval=self._interval)
        try:
            await self._client.create_schedule(schedule_id, schedule)
        except ScheduleAlreadyRunningError:
            pass
        else:
            return
        handle = self._client.get_schedule_handle(schedule_id)

        def replace(_: ScheduleUpdateInput, new: Schedule = schedule) -> ScheduleUpdate:
            return ScheduleUpdate(schedule=new)

        await handle.update(replace)
        await handle.unpause(note=schedule.state.note)

    async def _delete(self, catalog: str) -> None:
        try:
            await self._client.get_schedule_handle(table_discovery_schedule_id(catalog)).delete()
        except RPCError as error:
            if error.status != RPCStatusCode.NOT_FOUND:
                raise
