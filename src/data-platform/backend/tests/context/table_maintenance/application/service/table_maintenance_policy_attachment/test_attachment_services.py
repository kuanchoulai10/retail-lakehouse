"""Test the policy attachment and applicable policy services."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from context.table_maintenance.application.domain.model.table import Table, TableId, TableName
from context.table_maintenance.application.domain.model.table_discovery_rules import TableDiscoveryRuleId
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    DEFAULT_POLICY_NAME,
    MaintenancePolicyContent,
)
from context.table_maintenance.application.exceptions import ConflictError, NotFoundError
from context.table_maintenance.application.port.inbound.table_maintenance_policy import (
    CreateTableMaintenancePolicyUseCaseInput,
    DeleteTableMaintenancePolicyUseCaseInput,
    EnsureDefaultTableMaintenancePolicyUseCaseInput,
    ListTableMaintenancePoliciesUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_policy_attachment import (
    AttachTableMaintenancePolicyUseCaseInput,
    DetachTableMaintenancePolicyUseCaseInput,
    ListTableMaintenancePolicyAttachmentsUseCaseInput,
    ResolveApplicableTableMaintenancePolicyUseCaseInput,
)
from context.table_maintenance.application.port.outbound.table import CatalogNotFoundError
from context.table_maintenance.application.service.table_maintenance_policy import (
    CreateTableMaintenancePolicyService,
    DeleteTableMaintenancePolicyService,
    EnsureDefaultTableMaintenancePolicyService,
    ListTableMaintenancePoliciesService,
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
from tests.context.table_maintenance.fakes.in_memory_tables_repo import InMemoryTablesRepo
from tests.context.table_maintenance.fakes.recording_send_table_change_gateway import (
    RecordingSendTableChangeGateway,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CONTENT = MaintenancePolicyContent.platform_default().to_primitives()


class _World:
    def __init__(self) -> None:
        self.policies = InMemoryTableMaintenancePoliciesRepo()
        self.attachments = InMemoryTableMaintenancePolicyAttachmentsRepo()
        self.gateway = FakeReadTableMetadataGateway()
        self.tables = InMemoryTablesRepo()
        self.changes = RecordingSendTableChangeGateway()
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
            self.policies, self.attachments, self.gateway, self.tables, self.changes, clock=lambda: NOW
        )
        self._detach = DetachTableMaintenancePolicyService(
            self.policies, self.attachments, self.gateway, self.tables, self.changes
        )
        self._resolve = ResolveApplicableTableMaintenancePolicyService(
            self.policies, self.attachments, self.gateway, self.tables
        )
        self.list_attachments = ListTableMaintenancePolicyAttachmentsService(
            self.policies, self.attachments, self.gateway, self.tables
        )

    def attach(self, type_, path, policy):
        return self._attach.execute(
            AttachTableMaintenancePolicyUseCaseInput(target_type=type_, path=path, policy_name=policy)
        )

    def detach(self, type_, path, policy=None, table_uuid=None):
        return self._detach.execute(
            DetachTableMaintenancePolicyUseCaseInput(
                target_type=type_, path=path, policy_name=policy, table_uuid=table_uuid
            )
        )

    def resolve(self, table_uuid, catalog, namespace, table):
        return self._resolve.execute(
            ResolveApplicableTableMaintenancePolicyUseCaseInput(
                table_uuid=table_uuid, catalog=catalog, namespace=namespace, table=table
            )
        )

    def register_orders(self):
        self.tables.create(
            Table.register(
                TableId("u-1"),
                TableName(catalog="prod", namespace="sales.eu", table="orders"),
                TableDiscoveryRuleId.new(),
                NOW,
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
    items = world.list_attachments.execute(ListTableMaintenancePolicyAttachmentsUseCaseInput()).items
    assert [(i.policy_name, i.type) for i in items] == [("silver", "catalog")]


def test_attach_twice_to_one_target_replaces_not_duplicates(world):
    """A second attach finds the target's attachment by its key and replaces its policy, keeping its id."""
    world.attach("namespace", ("prod", "sales"), "gold")
    (first,) = world.attachments.list_all()
    world.attach("namespace", ("prod", "sales"), "silver")
    (stored,) = world.attachments.list_all()
    assert stored.id == first.id
    assert stored.policy_name.value == "silver"


def test_resolve_picks_table_over_namespace_over_catalog(world):
    """With all three attached the table's wins; detached, the namespace's; then the catalog's."""
    world.attach("catalog", ("prod",), "silver")
    world.attach("namespace", ("prod", "sales"), "gold")
    world.attach("table", ("prod", "sales", "eu", "orders"), DEFAULT_POLICY_NAME)
    assert world.resolve_orders().target["type"] == "table"
    world.detach("table", ("prod", "sales", "eu", "orders"), table_uuid="u-1")
    assert world.resolve_orders().target == {"type": "namespace", "path": ["prod", "sales"]}
    world.detach("namespace", ("prod", "sales"))
    assert world.resolve_orders().policy_name == "silver"
    assert world.resolve_orders().target == {"type": "catalog", "path": ["prod"]}


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


def test_attach_to_parent_only_namespace_works(world):
    """A namespace whose tables all sit in child namespaces still exists; a name prefix does not count."""
    world.gateway.drop_table("prod", "sales", "customers")
    world.attach("namespace", ("prod", "sales"), "gold")
    assert world.resolve_orders().policy_name == "gold"
    with pytest.raises(NotFoundError):
        world.attach("namespace", ("prod", "sal"), "gold")


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


def test_detach_names_the_target_by_its_dotted_path(world):
    """The not-found texts join the tuple path with dots, never print it as a tuple."""
    with pytest.raises(NotFoundError, match=r"^no policy is attached to namespace prod\.sales$"):
        world.detach("namespace", ("prod", "sales"))
    world.attach("namespace", ("prod", "sales"), "gold")
    with pytest.raises(NotFoundError, match=r"^policy silver is not attached to namespace prod\.sales$"):
        world.detach("namespace", ("prod", "sales"), "silver")


def test_list_filters_by_policy(world):
    """Listing can be limited to one policy."""
    world.attach("catalog", ("prod",), "gold")
    world.attach("namespace", ("prod", "sales"), "silver")
    items = world.list_attachments.execute(
        ListTableMaintenancePolicyAttachmentsUseCaseInput(policy_name="silver")
    ).items
    assert [i.path for i in items] == [("prod", "sales")]


def test_list_for_an_unknown_policy_is_not_found(world):
    """Listing the attachments of a policy that does not exist answers NotFoundError."""
    with pytest.raises(NotFoundError):
        world.list_attachments.execute(ListTableMaintenancePolicyAttachmentsUseCaseInput(policy_name="nope"))


def test_delete_attached_policy_conflicts(world):
    """A policy with an attachment cannot be deleted; detaching frees it."""
    world.attach("catalog", ("prod",), "gold")
    service = DeleteTableMaintenancePolicyService(world.policies, world.attachments)
    with pytest.raises(ConflictError):
        service.execute(DeleteTableMaintenancePolicyUseCaseInput(name="gold"))
    world.detach("catalog", ("prod",))
    service.execute(DeleteTableMaintenancePolicyUseCaseInput(name="gold"))


def test_attach_to_catalog_the_gateway_cannot_open_is_404(world, monkeypatch):
    """A catalog unknown to the gateway answers NotFoundError for catalog, namespace and table targets."""

    def unknown(_input):
        raise CatalogNotFoundError("nope")

    monkeypatch.setattr(world.gateway, "list_tables", unknown)
    monkeypatch.setattr(world.gateway, "load_table", lambda _ref: (_ for _ in ()).throw(CatalogNotFoundError("nope")))
    for type_, path in [("catalog", ("nope",)), ("namespace", ("nope", "a")), ("table", ("nope", "a", "t"))]:
        with pytest.raises(NotFoundError):
            world.attach(type_, path, "gold")


def test_detach_of_another_policy_is_404_and_keeps_the_attachment(world):
    """Detaching a policy that is not the one attached there answers NotFoundError and changes nothing."""
    world.attach("namespace", ("prod", "sales"), "gold")
    with pytest.raises(NotFoundError):
        world.detach("namespace", ("prod", "sales"), policy="silver")
    assert len(world.attachments.list_all()) == 1
    world.detach("namespace", ("prod", "sales"), policy="gold")
    assert world.attachments.list_all() == []


def test_detach_a_dropped_table_by_uuid(world):
    """A table gone from the catalog is detached by the uuid its attachment carries."""
    world.attach("table", ("prod", "sales", "eu", "orders"), "gold")
    world.gateway.drop_table("prod", "sales.eu", "orders")
    world.detach("table", ("prod", "sales", "eu", "orders"), policy="gold", table_uuid="u-1")
    assert world.attachments.list_all() == []


def _orphaned(world):
    items = world.list_attachments.execute(ListTableMaintenancePolicyAttachmentsUseCaseInput()).items
    return {(i.type, i.path): i.orphaned for i in items}


def test_list_marks_attachments_whose_target_left_the_catalog_orphaned(world):
    """An attachment is orphaned once its catalog, namespace or table is no longer in the catalog."""
    world.attach("catalog", ("prod",), "gold")
    world.attach("namespace", ("prod", "sales", "eu"), "gold")
    world.attach("namespace", ("prod", "sales"), "silver")
    world.attach("table", ("prod", "sales", "customers"), "gold")
    assert set(_orphaned(world).values()) == {False}
    world.gateway.drop_table("prod", "sales.eu", "orders")
    world.gateway.drop_table("prod", "sales", "customers")
    assert _orphaned(world) == {
        ("catalog", ("prod",)): True,
        ("namespace", ("prod", "sales", "eu")): True,
        ("namespace", ("prod", "sales")): True,
        ("table", ("prod", "sales", "customers")): True,
    }


def test_list_keeps_a_renamed_table_attachment_not_orphaned(world):
    """A table attachment follows the uuid: a table table maintenance knows, renamed, is still in the catalog."""
    world.register_orders()
    world.attach("table", ("prod", "sales", "eu", "orders"), "gold")
    world.gateway.drop_table("prod", "sales.eu", "orders")
    world.gateway.add_table("prod", "sales.eu", "orders_v2", "u-1")
    assert _orphaned(world) == {("table", ("prod", "sales", "eu", "orders")): False}


def test_list_marks_a_table_recreated_under_the_same_name_orphaned(world):
    """A new table under the old name has another uuid, so the old table's attachment is orphaned."""
    world.attach("table", ("prod", "sales", "eu", "orders"), "gold")
    world.gateway.drop_table("prod", "sales.eu", "orders")
    world.gateway.add_table("prod", "sales.eu", "orders", "u-new")
    assert _orphaned(world) == {("table", ("prod", "sales", "eu", "orders")): True}


def test_list_marks_attachments_of_an_unknown_catalog_orphaned(world, monkeypatch):
    """A catalog the gateway no longer knows leaves its attachments orphaned instead of failing the list."""
    world.attach("catalog", ("prod",), "gold")

    def unknown(_input):
        raise CatalogNotFoundError("prod")

    monkeypatch.setattr(world.gateway, "list_tables", unknown)
    assert _orphaned(world) == {("catalog", ("prod",)): True}


def test_resolve_by_uuid_alone_reads_the_registered_table(world):
    """A known table's uuid is enough: its name comes from the registered table."""
    world.register_orders()
    world.attach("namespace", ("prod", "sales"), "gold")
    out = world._resolve.execute(ResolveApplicableTableMaintenancePolicyUseCaseInput(table_uuid="u-1"))
    assert (out.policy_name, out.target) == ("gold", {"type": "namespace", "path": ["prod", "sales"]})
    with pytest.raises(NotFoundError):
        world._resolve.execute(ResolveApplicableTableMaintenancePolicyUseCaseInput(table_uuid="u-unknown"))


def test_list_policies_counts_attachments(world):
    """Each listed policy carries how many targets it is attached to."""
    world.attach("catalog", ("prod",), "gold")
    world.attach("namespace", ("prod", "sales"), "gold")
    listed = ListTableMaintenancePoliciesService(world.policies, world.attachments).execute(
        ListTableMaintenancePoliciesUseCaseInput()
    )
    assert {i.name: i.attachment_count for i in listed.items} == {DEFAULT_POLICY_NAME: 0, "gold": 2, "silver": 0}
