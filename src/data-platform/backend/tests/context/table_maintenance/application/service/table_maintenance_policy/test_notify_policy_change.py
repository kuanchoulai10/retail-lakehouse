"""Test that policy updates, attaches and detaches wake exactly the managed tables whose policy changed."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from context.table_maintenance.application.domain.model.shared import TableId
from context.table_maintenance.application.domain.model.table import Table, TableChange, TableName
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    DEFAULT_POLICY_NAME,
    MaintenancePolicyContent,
)
from context.table_maintenance.application.port.inbound.table_maintenance_policy import (
    AttachTableMaintenancePolicyUseCaseInput,
    CreateTableMaintenancePolicyUseCaseInput,
    DetachTableMaintenancePolicyUseCaseInput,
    EnsureDefaultTableMaintenancePolicyUseCaseInput,
    UpdateTableMaintenancePolicyUseCaseInput,
)
from context.table_maintenance.application.port.outbound.table import (
    SendTableChangeGateway,
    SendTableChangeGatewayInput,
)
from context.table_maintenance.application.service.table_maintenance_policy import (
    AttachTableMaintenancePolicyService,
    CreateTableMaintenancePolicyService,
    DetachTableMaintenancePolicyService,
    EnsureDefaultTableMaintenancePolicyService,
    UpdateTableMaintenancePolicyService,
    notify_policy_change,
)
from tests.context.table_maintenance.discovery_decision_samples import MANAGED, UNMANAGED
from tests.context.table_maintenance.fakes.fake_read_table_metadata_gateway import (
    FakeReadTableMetadataGateway,
)
from tests.context.table_maintenance.fakes.in_memory_catalogs_repo import InMemoryCatalogsRepo
from tests.context.table_maintenance.fakes.in_memory_namespaces_repo import InMemoryNamespacesRepo
from tests.context.table_maintenance.fakes.in_memory_table_maintenance_policies_repo import (
    InMemoryTableMaintenancePoliciesRepo,
)
from tests.context.table_maintenance.fakes.in_memory_tables_repo import InMemoryTablesRepo
from tests.context.table_maintenance.fakes.recording_send_table_change_gateway import (
    RecordingSendTableChangeGateway,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CONTENT = MaintenancePolicyContent.platform_default().to_primitives()


class _World:
    def __init__(self) -> None:
        self.policies = InMemoryTableMaintenancePoliciesRepo()
        self.catalogs = InMemoryCatalogsRepo()
        self.namespaces = InMemoryNamespacesRepo()
        self.tables = InMemoryTablesRepo()
        self.catalog = FakeReadTableMetadataGateway()
        self.changes = RecordingSendTableChangeGateway()
        EnsureDefaultTableMaintenancePolicyService(self.policies, clock=lambda: NOW).execute(
            EnsureDefaultTableMaintenancePolicyUseCaseInput()
        )
        CreateTableMaintenancePolicyService(self.policies, clock=lambda: NOW).execute(
            CreateTableMaintenancePolicyUseCaseInput(name="gold", content=CONTENT)
        )
        self.add_table("u-eu", "sales.eu", "orders")
        self.add_table("u-us", "sales.us", "orders")

    def add_table(self, uuid: str, namespace: str, table: str, *, managed: bool = True, catalog: str = "prod") -> None:
        self.catalog.add_table(catalog, namespace, table, uuid)
        registered = Table.register(
            TableId(uuid), TableName(catalog=catalog, namespace=namespace, table=table), MANAGED, NOW
        )
        if not managed:
            registered.unmanage(UNMANAGED.decided_by, NOW)
        self.tables.create(registered)

    def attach(self, type_: str, path: tuple[str, ...], policy: str) -> None:
        AttachTableMaintenancePolicyService(
            self.policies, self.catalogs, self.namespaces, self.tables, self.catalog, self.changes, clock=lambda: NOW
        ).execute(AttachTableMaintenancePolicyUseCaseInput(target_type=type_, path=path, policy_name=policy))

    def detach(self, type_: str, path: tuple[str, ...], policy: str) -> None:
        DetachTableMaintenancePolicyService(
            self.policies, self.catalogs, self.namespaces, self.tables, self.changes, clock=lambda: NOW
        ).execute(DetachTableMaintenancePolicyUseCaseInput(policy_name=policy, target_type=type_, path=path))

    def update(self, name: str, version: int) -> None:
        UpdateTableMaintenancePolicyService(
            self.policies, self.catalogs, self.namespaces, self.tables, self.changes, clock=lambda: NOW
        ).execute(UpdateTableMaintenancePolicyUseCaseInput(name=name, content=CONTENT, version=version))

    def woken(self) -> list[str]:
        assert all(c.change == TableChange.POLICY_CHANGED.value for c in self.changes.calls)
        return sorted(c.table_uuid for c in self.changes.calls)


@pytest.fixture
def world() -> _World:
    """Provide two managed tables in different namespaces of catalog prod."""
    return _World()


def test_attach_wakes_only_tables_whose_policy_changed(world: _World) -> None:
    """Attaching to one namespace wakes only the table in it, once, as a policy change."""
    world.attach("namespace", ("prod", "sales", "eu"), "gold")
    assert world.changes.calls == [
        SendTableChangeGatewayInput(
            table_uuid="u-eu",
            table_name="prod.sales.eu.orders",
            change=TableChange.POLICY_CHANGED.value,
            is_managed=True,
        )
    ]


def test_attach_to_a_namespace_wakes_only_its_tables_with_no_nearer_policy(world: _World) -> None:
    """Under a namespace, a table holding its own policy or under a deeper namespace holding one is not woken.

    ``u-eu`` holds a policy itself and ``sales.us`` holds one; ``u-eu2`` and ``u-asia`` have none nearer than
    ``sales``, so they alone change; ``u-other`` lives in another catalog.
    """
    world.add_table("u-eu2", "sales.eu", "events")
    world.add_table("u-asia", "sales.asia", "orders")
    world.add_table("u-other", "sales.eu", "orders", catalog="dev")
    world.attach("table", ("prod", "sales", "eu", "orders"), DEFAULT_POLICY_NAME)
    world.attach("namespace", ("prod", "sales", "us"), DEFAULT_POLICY_NAME)
    world.changes.calls.clear()

    world.attach("namespace", ("prod", "sales"), "gold")

    assert world.woken() == ["u-asia", "u-eu2"]


def test_attach_to_a_table_wakes_that_table(world: _World) -> None:
    """A policy attached to a managed table moves only that table."""
    world.attach("table", ("prod", "sales", "us", "orders"), "gold")

    assert world.woken() == ["u-us"]


def test_update_default_wakes_tables_without_attachment(world: _World) -> None:
    """A new version of the default policy wakes every table that falls back to it, and no other."""
    world.attach("namespace", ("prod", "sales", "eu"), "gold")
    world.changes.calls.clear()
    world.update(DEFAULT_POLICY_NAME, 1)
    assert world.woken() == ["u-us"]


def test_update_attached_policy_wakes_the_tables_it_applies_to(world: _World) -> None:
    """A new version of an attached policy wakes the tables that resolve to it."""
    world.attach("catalog", ("prod",), "gold")
    world.changes.calls.clear()
    world.update("gold", 1)
    assert world.woken() == ["u-eu", "u-us"]


def test_attaching_the_same_policy_again_wakes_nothing(world: _World) -> None:
    """Re-attaching the policy a place already holds changes no table's policy."""
    world.attach("catalog", ("prod",), "gold")
    world.changes.calls.clear()
    world.attach("catalog", ("prod",), "gold")
    assert world.changes.calls == []


def test_attach_under_a_nearer_attachment_wakes_nothing(world: _World) -> None:
    """A catalog attachment does not change a table whose namespace holds its own."""
    world.attach("namespace", ("prod", "sales", "eu"), "gold")
    world.attach("namespace", ("prod", "sales", "us"), DEFAULT_POLICY_NAME)
    world.changes.calls.clear()
    world.attach("catalog", ("prod",), "gold")
    assert world.changes.calls == []


def test_detach_wakes_the_tables_falling_back(world: _World) -> None:
    """Detaching wakes the tables that now resolve to another policy."""
    world.attach("table", ("prod", "sales", "us", "orders"), "gold")
    world.changes.calls.clear()
    world.detach("table", ("prod", "sales", "us", "orders"), "gold")
    assert world.woken() == ["u-us"]


def test_unmanaged_tables_are_not_woken(world: _World) -> None:
    """Only managed tables have a reconciliation to wake."""
    world.add_table("u-off", "sales.eu", "events", managed=False)
    world.attach("namespace", ("prod", "sales", "eu"), "gold")
    assert world.woken() == ["u-eu"]


class _FailingFirstSend(SendTableChangeGateway):
    """Fail the first send, record the others."""

    def __init__(self) -> None:
        self.attempts = 0
        self.sent: list[str] = []

    def send(self, input: SendTableChangeGatewayInput) -> None:  # noqa: A002
        self.attempts += 1
        if self.attempts == 1:
            raise RuntimeError("runtime down")
        self.sent.append(input.table_uuid)


def test_a_failed_wake_does_not_undo_the_change_or_stop_other_wakes(world: _World) -> None:
    """Waking is best effort: a failed send is logged, the change stands and other tables are still woken."""
    world.attach("catalog", ("prod",), "gold")
    failing = _FailingFirstSend()

    def change() -> str:
        world.attach("catalog", ("prod",), DEFAULT_POLICY_NAME)
        return "done"

    result = notify_policy_change(world.tables, world.policies, world.catalogs, world.namespaces, failing, change)
    assert result == "done"
    assert failing.attempts == 2
    assert len(failing.sent) == 1


def test_a_refused_change_wakes_nothing(world: _World) -> None:
    """A change that raises is not committed, so no table is told and the error propagates."""

    def change() -> None:
        raise RuntimeError("refused")

    with pytest.raises(RuntimeError, match="refused"):
        notify_policy_change(world.tables, world.policies, world.catalogs, world.namespaces, world.changes, change)

    assert world.changes.calls == []
