"""Test that non-NOT_FOUND RPC errors propagate out of the Temporal gateways."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from types import SimpleNamespace

import pytest
from temporalio.client import RPCError
from temporalio.service import RPCStatusCode

from adapter.hybrid.temporal.outbound.table_discovery_settings import (
    UpdateTableDiscoveryScheduleTemporalGateway,
)
from adapter.hybrid.temporal.outbound.shared import AsyncLoopBridge
from adapter.hybrid.temporal.outbound.table_maintenance_run import (
    SendMaintenanceResultTemporalGateway,
)
from adapter.hybrid.temporal.outbound.table import SendTableChangeTemporalGateway
from adapter.hybrid.temporal.contracts import table_discovery_schedule_id
from application.exceptions import NotFoundError
from application.port.outbound.table_discovery_settings import (
    UpdateTableDiscoveryScheduleGatewayInput,
)
from application.port.outbound.table_maintenance_run import (
    SendMaintenanceResultGatewayInput,
)
from application.port.outbound.table import SendTableChangeGatewayInput


class _FailingHandle:
    def __init__(self, status: RPCStatusCode) -> None:
        self._status = status

    async def signal(self, *args: object, **kwargs: object) -> None:
        raise RPCError("rpc failed", self._status, b"")

    async def pause(self, **kwargs: object) -> None:
        raise RPCError("rpc failed", self._status, b"")

    async def unpause(self, **kwargs: object) -> None:
        raise RPCError("rpc failed", self._status, b"")


class _FailingClient:
    def __init__(self, status: RPCStatusCode) -> None:
        self._handle = _FailingHandle(status)

    def get_workflow_handle(self, *args: object, **kwargs: object) -> _FailingHandle:
        return self._handle

    def get_schedule_handle(self, *args: object, **kwargs: object) -> _FailingHandle:
        return self._handle

    async def list_schedules(self, *args: object, **kwargs: object) -> AsyncIterator:
        async def listing() -> AsyncIterator[SimpleNamespace]:
            yield SimpleNamespace(id=table_discovery_schedule_id("iceberg"))

        return listing()


@pytest.fixture
def bridge() -> Iterator[AsyncLoopBridge]:
    bridge = AsyncLoopBridge()
    yield bridge
    bridge.close()


def _result_input() -> SendMaintenanceResultGatewayInput:
    return SendMaintenanceResultGatewayInput("wf-r1", "r1", "op", 1, True, {}, None)


def test_table_change_propagates_other_rpc_errors(bridge):
    client = _FailingClient(RPCStatusCode.INVALID_ARGUMENT)
    gateway = SendTableChangeTemporalGateway(client, bridge)  # ty: ignore[invalid-argument-type]
    with pytest.raises(RPCError):
        gateway.send(
            SendTableChangeGatewayInput(
                "u", "iceberg.sales.u", "settings_changed", is_enrolled=False
            )
        )


def test_maintenance_result_propagates_other_rpc_errors(bridge):
    client = _FailingClient(RPCStatusCode.INVALID_ARGUMENT)
    gateway = SendMaintenanceResultTemporalGateway(client, bridge)  # ty: ignore[invalid-argument-type]
    with pytest.raises(RPCError):
        gateway.send(_result_input())


def test_maintenance_result_not_found_maps_to_not_found_error(bridge):
    client = _FailingClient(RPCStatusCode.NOT_FOUND)
    gateway = SendMaintenanceResultTemporalGateway(client, bridge)  # ty: ignore[invalid-argument-type]
    with pytest.raises(NotFoundError):
        gateway.send(_result_input())


@pytest.mark.parametrize("paused", [True, False])
def test_schedule_update_propagates_other_rpc_errors(bridge, paused):
    client = _FailingClient(RPCStatusCode.INVALID_ARGUMENT)
    gateway = UpdateTableDiscoveryScheduleTemporalGateway(client, bridge)  # ty: ignore[invalid-argument-type]
    with pytest.raises(RPCError):
        gateway.update(UpdateTableDiscoveryScheduleGatewayInput(paused=paused))
