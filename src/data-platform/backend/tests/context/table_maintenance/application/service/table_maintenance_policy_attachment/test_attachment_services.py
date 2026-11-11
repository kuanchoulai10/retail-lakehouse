"""Test the policy attachment and applicable policy services."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    DEFAULT_POLICY_NAME,
    MaintenancePolicyContent,
)
from context.table_maintenance.application.exceptions import ConflictError, NotFoundError
from context.table_maintenance.application.port.inbound.table_maintenance_policy import (
    CreateTableMaintenancePolicyUseCaseInput,
    DeleteTableMaintenancePolicyUseCaseInput,
    EnsureDefaultTableMaintenancePolicyUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_policy_attachment import (
    AttachTableMaintenancePolicyUseCaseInput,
    DetachTableMaintenancePolicyUseCaseInput,
    ListTableMaintenancePolicyAttachmentsUseCaseInput,
    ResolveApplicableTableMaintenancePolicyUseCaseInput,
)
from context.table_maintenance.application.service.table_maintenance_policy import (
    CreateTableMaintenancePolicyService,
    DeleteTableMaintenancePolicyService,
    EnsureDefaultTableMaintenancePolicyService,
)
from context.table_maintenance.application.service.table_maintenance_policy_attachment import (
    AttachTableMaintenancePolicyService,
    DetachTableMaintenancePolicyService,
    ListTableMaintenancePolicyAttachmentsService,
    ResolveApplicableTableMaintenancePolicyService,
)
from tests.context.table_maintenance.fakes.fake_read_table_metadata_gateway import (
    FakeReadTableMetadataGateway,
)
from tests.context.table_maintenance.fakes.in_memory_table_maintenance_policies_repo import (
    InMemoryTableMaintenancePoliciesRepo,
)
from tests.context.table_maintenance.fakes.in_memory_table_maintenance_policy_attachments_repo import (
    InMemoryTableMaintenancePolicyAttachmentsRepo,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CONTENT = MaintenancePolicyContent.platform_default().to_primitives()


class _World:
    def __init__(self) -> None:
        self.policies = InMemoryTableMaintenancePoliciesRepo()
        self.attachments = InMemoryTableMaintenancePolicyAttachmentsRepo()
        self.gateway = FakeReadTableMetadataGateway()
        self.gateway.add_table("prod", "sales.eu", "orders", "u-1")
        self.gateway.add_table("prod", "sales", "customers", "u-2")
        EnsureDefaultTableMaintenancePolicyService(self.policies, clock=lambda: NOW).execute(
            EnsureDefaultTableMaintenancePolicyUseCaseInput()
        )
        for name in ("gold", "silver"):
            CreateTableMaintenancePolicyService(self.policies, clock=lambda: NOW).execute(
                CreateTableMaintenancePolicyUseCaseInput(name=name, content=CONTENT)
            )
        self._attach = AttachTableMaintenancePolicyService(
            self.policies, self.attachments, self.gateway, clock=lambda: NOW
        )
        self._detach = DetachTableMaintenancePolicyService(self.attachments, self.gateway)
        self._resolve = ResolveApplicableTableMaintenancePolicyService(self.policies, self.attachments, self.gateway)

    def attach(self, type_, path, policy):
        return self._attach.execute(
            AttachTableMaintenancePolicyUseCaseInput(target_type=type_, path=path, policy_name=policy)
        )

    def detach(self, type_, path):
        return self._detach.execute(DetachTableMaintenancePolicyUseCaseInput(target_type=type_, path=path))

    def resolve(self, table_uuid, catalog, namespace, table):
        return self._resolve.execute(
            ResolveApplicableTableMaintenancePolicyUseCaseInput(
                table_uuid=table_uuid, catalog=catalog, namespace=namespace, table=table
            )
        )

    def resolve_orders(self):
        return self.resolve("u-1", "prod", "sales.eu", "orders")


@pytest.fixture
def world() -> _World:
    """Provide services over fakes with a prod catalog holding two tables."""
    return _World()


def test_no_attachment_falls_back_to_default(world):
    """With nothing attached the default policy applies and the target is None."""
    out = world.resolve_orders()
    assert out.policy_name == DEFAULT_POLICY_NAME
    assert out.version == 1
    assert out.target is None


def test_deepest_attachment_wins(world):
    """A namespace attachment beats the catalog's for a table below both."""
    world.attach("catalog", ("prod",), "silver")
    world.attach("namespace", ("prod", "sales"), "gold")
    out = world.resolve_orders()
    assert out.policy_name == "gold"
    assert out.target == {"type": "namespace", "path": ["prod", "sales"]}


def test_table_attachment_beats_namespace(world):
    """A table attachment beats its namespace's."""
    world.attach("namespace", ("prod", "sales"), "gold")
    world.attach("table", ("prod", "sales", "eu", "orders"), "silver")
    out = world.resolve_orders()
    assert out.policy_name == "silver"
    assert out.target is not None
    assert out.target["type"] == "table"


def test_default_attachment_overrides_catalog_attachment(world):
    """Attaching default to a namespace overrides the catalog's policy there."""
    world.attach("catalog", ("prod",), "gold")
    world.attach("namespace", ("prod", "sales"), DEFAULT_POLICY_NAME)
    out = world.resolve_orders()
    assert out.policy_name == DEFAULT_POLICY_NAME
    assert out.target == {"type": "namespace", "path": ["prod", "sales"]}


def test_rename_keeps_table_attachment_and_follows_namespace(world):
    """The table attachment follows the uuid; namespace attachments follow the new name."""
    world.attach("table", ("prod", "sales", "eu", "orders"), "silver")
    world.attach("namespace", ("prod", "sales"), "gold")
    world.gateway.add_table("prod", "archive", "orders_old", "u-9")
    world.attach("namespace", ("prod", "archive"), "gold")
    world.gateway.drop_table("prod", "sales.eu", "orders")
    world.gateway.add_table("prod", "archive", "orders_renamed", "u-1")
    assert world.resolve("u-1", "prod", "archive", "orders_renamed").policy_name == "silver"
    world.gateway.add_table("prod", "archive", "other", "u-3")
    assert world.resolve("u-3", "prod", "archive", "other").target == {"type": "namespace", "path": ["prod", "archive"]}


def test_resolve_for_a_namespace_starts_at_that_namespace(world):
    """A namespace query ignores table attachments and starts at the namespace."""
    world.attach("catalog", ("prod",), "silver")
    world.attach("table", ("prod", "sales", "eu", "orders"), "gold")
    out = world.resolve(None, "prod", "sales.eu", None)
    assert out.policy_name == "silver"
    assert out.target == {"type": "catalog", "path": ["prod"]}


def test_resolve_by_table_name_looks_up_the_uuid(world):
    """Without a uuid the table's uuid is read from the catalog."""
    world.attach("table", ("prod", "sales", "eu", "orders"), "gold")
    assert world.resolve(None, "prod", "sales.eu", "orders").policy_name == "gold"


def test_attach_replaces_existing_attachment_on_target(world):
    """Attaching again to one target moves it to the new policy."""
    world.attach("catalog", ("prod",), "gold")
    world.attach("catalog", ("prod",), "silver")
    items = (
        ListTableMaintenancePolicyAttachmentsService(world.attachments)
        .execute(ListTableMaintenancePolicyAttachmentsUseCaseInput())
        .items
    )
    assert [(i.policy_name, i.type) for i in items] == [("silver", "catalog")]


@pytest.mark.parametrize(
    ("type_", "path"),
    [
        ("catalog", ("nope",)),
        ("namespace", ("prod", "missing")),
        ("table", ("prod", "sales", "ghost")),
    ],
)
def test_attach_to_missing_target_is_404(world, type_, path):
    """A catalog, namespace or table missing from the catalog answers NotFoundError."""
    with pytest.raises(NotFoundError):
        world.attach(type_, path, "gold")
    assert world.attachments.list_all() == []


def test_attach_missing_policy_is_404(world):
    """Attaching an unknown policy answers NotFoundError."""
    with pytest.raises(NotFoundError):
        world.attach("catalog", ("prod",), "nope")


def test_detach_removes_and_missing_is_404(world):
    """Detach removes the attachment; detaching again answers NotFoundError."""
    world.attach("namespace", ("prod", "sales"), "gold")
    world.detach("namespace", ("prod", "sales"))
    assert world.attachments.list_all() == []
    with pytest.raises(NotFoundError):
        world.detach("namespace", ("prod", "sales"))


def test_list_filters_by_policy(world):
    """Listing can be limited to one policy."""
    world.attach("catalog", ("prod",), "gold")
    world.attach("namespace", ("prod", "sales"), "silver")
    items = (
        ListTableMaintenancePolicyAttachmentsService(world.attachments)
        .execute(ListTableMaintenancePolicyAttachmentsUseCaseInput(policy_name="silver"))
        .items
    )
    assert [i.path for i in items] == [("prod", "sales")]


def test_delete_attached_policy_conflicts(world):
    """A policy with an attachment cannot be deleted; detaching frees it."""
    world.attach("catalog", ("prod",), "gold")
    service = DeleteTableMaintenancePolicyService(world.policies, world.attachments)
    with pytest.raises(ConflictError):
        service.execute(DeleteTableMaintenancePolicyUseCaseInput(name="gold"))
    world.detach("catalog", ("prod",))
    service.execute(DeleteTableMaintenancePolicyUseCaseInput(name="gold"))
