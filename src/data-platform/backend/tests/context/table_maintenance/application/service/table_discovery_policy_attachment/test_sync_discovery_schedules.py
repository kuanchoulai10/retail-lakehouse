"""Test the full schedule reconcile the worker runs at start."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from context.table_maintenance.application.domain.model.shared import PolicyTarget, PolicyTargetType, TableId
from context.table_maintenance.application.domain.model.table import Table, TableName
from context.table_maintenance.application.domain.model.table_discovery_policy import TableDiscoveryPolicyName
from context.table_maintenance.application.domain.model.table_discovery_policy_attachment import (
    TableDiscoveryPolicyAttachment,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy import (
    CreateTableDiscoveryPolicyUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy_attachment import (
    SyncDiscoverySchedulesUseCaseInput,
    SyncDiscoverySchedulesUseCaseOutput,
)
from context.table_maintenance.application.port.outbound.table import SendDiscoveryRequestGatewayInput
from context.table_maintenance.application.port.outbound.table_discovery_policy_attachment import (
    SyncDiscoverySchedulesGatewayInput,
)
from context.table_maintenance.application.service.table_discovery_policy import (
    CreateTableDiscoveryPolicyService,
)
from context.table_maintenance.application.service.table_discovery_policy_attachment import (
    SyncDiscoverySchedulesService,
)
from tests.context.table_maintenance.application.domain.service.table_discovery_policy_attachment.discovery_policy_samples import (  # noqa: E501
    MANAGE_ALL as MANAGE_ALL_SAMPLE,
)
from tests.context.table_maintenance.fakes.in_memory_table_discovery_policies_repo import (
    InMemoryTableDiscoveryPoliciesRepo,
)
from tests.context.table_maintenance.fakes.in_memory_table_discovery_policy_attachments_repo import (
    InMemoryTableDiscoveryPolicyAttachmentsRepo,
)
from tests.context.table_maintenance.fakes.in_memory_tables_repo import InMemoryTablesRepo
from tests.context.table_maintenance.fakes.recording_send_discovery_request_gateway import (
    RecordingSendDiscoveryRequestGateway,
)
from tests.context.table_maintenance.fakes.recording_sync_discovery_schedules_gateway import (
    RecordingSyncDiscoverySchedulesGateway,
)

NOW = datetime(2026, 11, 1, tzinfo=UTC)


class _World:
    """Hold ``manage-all`` attached to the catalog ``iceberg``; nothing is attached in ``lake``.

    The schedules start as ``scheduled``: ``iceberg`` is scanned, ``lake`` is not.
    """

    def __init__(self, scheduled: tuple[str, ...]) -> None:
        self.attachments = InMemoryTableDiscoveryPolicyAttachmentsRepo()
        self.policies = InMemoryTableDiscoveryPoliciesRepo()
        self.tables = InMemoryTablesRepo()
        self.requests = RecordingSendDiscoveryRequestGateway()
        self.schedules = RecordingSyncDiscoverySchedulesGateway(scheduled)
        CreateTableDiscoveryPolicyService(self.policies, clock=lambda: NOW).execute(
            CreateTableDiscoveryPolicyUseCaseInput(
                name="manage-all", description="", rules=({"action": "include", "table_name_pattern": "*"},)
            )
        )
        manage_all = self.policies.get_by_name(TableDiscoveryPolicyName(value="manage-all"))
        assert manage_all is not None
        target = PolicyTarget(type=PolicyTargetType.CATALOG, path=("iceberg",))
        self.attachments.create(TableDiscoveryPolicyAttachment.attach(target, manage_all.id, NOW))

    def manage(self, uuid: str, catalog: str) -> None:
        """Store a table of ``catalog`` as managed."""
        name = TableName(catalog=catalog, namespace="sales", table=uuid)
        self.tables.create(Table.register(TableId(uuid), name, MANAGE_ALL_SAMPLE.should_manage(name), NOW))

    def sync(self) -> SyncDiscoverySchedulesUseCaseOutput:
        return SyncDiscoverySchedulesService(
            self.policies,
            self.attachments,
            self.tables,
            self.requests,
            self.schedules,
            new_change_id=lambda: "start",
        ).execute(SyncDiscoverySchedulesUseCaseInput())


def test_sync_creates_the_missing_schedules() -> None:
    """A scanned catalog without a schedule gets one, and nothing is scanned."""
    world = _World(scheduled=())

    out = world.sync()

    assert out.catalogs == ("iceberg",)
    assert world.schedules.synced == [SyncDiscoverySchedulesGatewayInput(catalogs=("iceberg",), removed=())]
    assert world.requests.calls == []


def test_sync_gives_each_catalog_that_left_its_final_scan_then_deletes_its_schedule() -> None:
    """A schedule of a catalog no longer scanned is deleted only after that catalog's final scan is started."""
    world = _World(scheduled=("gone", "iceberg", "lake"))

    world.sync()

    assert world.requests.calls == [
        SendDiscoveryRequestGatewayInput("gone", None, change_id="start", retires_schedule=True),
        SendDiscoveryRequestGatewayInput("lake", None, change_id="start", retires_schedule=True),
    ]
    assert world.schedules.synced == [
        SyncDiscoverySchedulesGatewayInput(catalogs=("iceberg",), removed=("gone", "lake"))
    ]
    assert world.schedules.scheduled == {"iceberg"}


def test_a_final_scan_that_cannot_start_fails_the_sync_and_deletes_nothing() -> None:
    """The worker start fails loudly, and the schedule of the catalog that left stays for the next start."""
    world = _World(scheduled=("gone", "iceberg"))
    world.requests.failing.add("gone")

    with pytest.raises(RuntimeError, match="gone"):
        world.sync()

    assert world.schedules.synced == []
    assert world.schedules.scheduled == {"gone", "iceberg"}


def test_a_failed_schedule_sync_propagates() -> None:
    """A sync the schedules refuse fails the worker start."""
    world = _World(scheduled=())
    world.schedules.failing = True

    with pytest.raises(RuntimeError, match="temporal is down"):
        world.sync()


def test_a_catalog_holding_managed_tables_but_not_scanned_gets_its_final_scan() -> None:
    """A catalog with managed tables and no managing policy gets a final scan even without a schedule."""
    world = _World(scheduled=("iceberg",))
    world.manage("u-1", "orphaned")
    world.manage("u-2", "orphaned")
    world.manage("u-3", "iceberg")

    world.sync()

    assert world.requests.calls == [
        SendDiscoveryRequestGatewayInput("orphaned", None, change_id="start", retires_schedule=True)
    ]
    assert world.schedules.synced == [SyncDiscoverySchedulesGatewayInput(catalogs=("iceberg",), removed=("orphaned",))]
