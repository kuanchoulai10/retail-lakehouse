"""Test that non-NOT_FOUND RPC errors propagate out of the Temporal gateways."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from temporalio.client import RPCError
from temporalio.service import RPCStatusCode

from context.table_maintenance.adapter.hybrid.temporal.outbound.shared import (
    AsyncLoopBridge,
)
from context.table_maintenance.adapter.hybrid.temporal.outbound.table import (
    SendDiscoveryRequestTemporalGateway,
    SendTableChangeTemporalGateway,
)
from context.table_maintenance.adapter.hybrid.temporal.outbound.table_maintenance_run import (
    SendMaintenanceResultTemporalGateway,
)
from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.outbound.table import (
    SendDiscoveryRequestGatewayInput,
    SendTableChangeGatewayInput,
)
from context.table_maintenance.application.port.outbound.table_maintenance_run import (
    SendMaintenanceResultGatewayInput,
)

if TYPE_CHECKING:
    from collections.abc import Iterator


class _FailingHandle:
    def __init__(self, status: RPCStatusCode) -> None:
        self._status = status

    async def signal(self, *args: object, **kwargs: object) -> None:
        raise RPCError("rpc failed", self._status, b"")


class _FailingClient:
    def __init__(self, status: RPCStatusCode) -> None:
        self._handle = _FailingHandle(status)
        self.started: list[str] = []
        self.signalled: list[str] = []

    async def start_workflow(self, *args: object, id: str, **kwargs: object) -> None:  # noqa: A002
        self.started.append(id)

    def get_workflow_handle(self, workflow_id: str, *args: object, **kwargs: object) -> _FailingHandle:
        self.signalled.append(workflow_id)
        return self._handle


@pytest.fixture
def bridge() -> Iterator[AsyncLoopBridge]:
    """Provide an async loop bridge that is closed after the test."""
    bridge = AsyncLoopBridge()
    yield bridge
    bridge.close()


def _result_input() -> SendMaintenanceResultGatewayInput:
    return SendMaintenanceResultGatewayInput("wf-r1", "r1", "op", 1, True, {}, None)


def test_table_change_propagates_other_rpc_errors(bridge):
    """The table change gateway raises RPC errors other than not found."""
    client = _FailingClient(RPCStatusCode.INVALID_ARGUMENT)
    gateway = SendTableChangeTemporalGateway(client, bridge)  # ty: ignore[invalid-argument-type]
    with pytest.raises(RPCError):
        gateway.send(SendTableChangeGatewayInput("u", "iceberg.sales.u", "policy_changed", is_managed=False))


def test_maintenance_result_propagates_other_rpc_errors(bridge):
    """The maintenance result gateway raises RPC errors other than not found."""
    client = _FailingClient(RPCStatusCode.INVALID_ARGUMENT)
    gateway = SendMaintenanceResultTemporalGateway(client, bridge)  # ty: ignore[invalid-argument-type]
    with pytest.raises(RPCError):
        gateway.send(_result_input())


def test_maintenance_result_not_found_maps_to_not_found_error(bridge):
    """A not found RPC error from the maintenance result gateway becomes a NotFoundError."""
    client = _FailingClient(RPCStatusCode.NOT_FOUND)
    gateway = SendMaintenanceResultTemporalGateway(client, bridge)  # ty: ignore[invalid-argument-type]
    with pytest.raises(NotFoundError):
        gateway.send(_result_input())


def test_namespace_request_ignores_a_catalog_scan_that_is_not_running(bridge):
    """The rescan asked of the catalog scan is dropped when no such scan runs; the namespace scan still starts."""
    client = _FailingClient(RPCStatusCode.NOT_FOUND)
    gateway = SendDiscoveryRequestTemporalGateway(client, bridge)  # ty: ignore[invalid-argument-type]

    gateway.send(SendDiscoveryRequestGatewayInput("lake", "sales", change_id="c1"))

    assert client.started == ["table-discovery:catalog=lake:namespace=sales:trigger=policy-changed:change=c1"]
    assert client.signalled == ["table-discovery:catalog=lake"]


def test_namespace_request_propagates_other_rpc_errors_of_the_catalog_rescan(bridge):
    """Any other error asking the catalog scan to rescan is raised, after the namespace scan started."""
    client = _FailingClient(RPCStatusCode.INVALID_ARGUMENT)
    gateway = SendDiscoveryRequestTemporalGateway(client, bridge)  # ty: ignore[invalid-argument-type]

    with pytest.raises(RPCError):
        gateway.send(SendDiscoveryRequestGatewayInput("lake", "sales", change_id="c1"))
    assert client.started == ["table-discovery:catalog=lake:namespace=sales:trigger=policy-changed:change=c1"]
