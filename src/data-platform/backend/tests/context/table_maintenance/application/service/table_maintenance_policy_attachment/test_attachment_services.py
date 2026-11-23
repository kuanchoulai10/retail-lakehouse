"""Test the policy attachment and applicable policy services."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from context.table_maintenance.application.domain.model.shared import TableId, TableMaintenancePolicyId
from context.table_maintenance.application.domain.model.table import Table, TableName
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    DEFAULT_POLICY_ID,
    DEFAULT_POLICY_NAME,
    MaintenancePolicyContent,
    TableMaintenancePolicyName,
)
from context.table_maintenance.application.exceptions import ConflictError, NotFoundError, ValidationError
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
from context.table_maintenance.application.port.outbound.table import CatalogAccessDeniedError
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
from tests.context.table_maintenance.discovery_decision_samples import MANAGED
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
        self._detach = DetachTableMaintenancePolicyService(self.policies, self.attachments, self.tables, self.changes)
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

    def detach(self, policy, attachment_id):
        return self._detach.execute(
            DetachTableMaintenancePolicyUseCaseInput(policy_name=policy, attachment_id=attachment_id)
        )

    def listed(self, *policies):
        """Return the listed attachments of ``policies`` (default: every policy but the default), in order."""
        return [
            item
            for policy in policies or ("gold", "silver")
            for item in self.list_attachments.execute(
                ListTableMaintenancePolicyAttachmentsUseCaseInput(policy_name=policy)
            ).items
        ]

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
                MANAGED,
                NOW,
            )
        )

    def resolve_orders(self):
        return self.resolve("u-1", "prod", "sales.eu", "orders")

    def policy_id(self, name: str) -> TableMaintenancePolicyId:
        policy = self.policies.get_by_name(TableMaintenancePolicyName(value=name))
        assert policy is not None
        return policy.id


@pytest.fixture
def world() -> _World:
    """Provide services over fakes with a prod catalog holding two tables."""
    return _World()


def test_no_attachment_falls_back_to_default(world):
    """With nothing attached the default policy applies and the target is None."""
    out = world.resolve_orders()
    assert (out.policy_id, out.policy_name) == (DEFAULT_POLICY_ID.value, DEFAULT_POLICY_NAME)
    assert out.version == 1
    assert out.target is None


def test_attachment_points_at_the_policy_id(world):
    """Attaching by name stores the policy's id; the answer names the policy by id and by its name."""
    out = world.attach("namespace", ("prod", "sales"), "gold")

    (stored,) = world.attachments.list_all()
    assert stored.policy_id == world.policy_id("gold")
    assert (out.policy_id, out.policy_name) == (world.policy_id("gold").value, "gold")


def test_resolve_names_the_attached_policy_by_id_and_name(world):
    """The applicable policy is found through the attachment's policy id and answered with both."""
    world.attach("namespace", ("prod", "sales"), "silver")

    out = world.resolve_orders()

    assert (out.policy_id, out.policy_name) == (world.policy_id("silver").value, "silver")


def test_list_attachments_name_the_policy_by_id_and_name(world):
    """Each listed attachment carries its policy's id and current name."""
    out = world.attach("catalog", ("prod",), "gold")

    (item,) = world.listed("gold")

    assert (item.id, item.policy_id, item.policy_name) == (out.id, world.policy_id("gold").value, "gold")


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
    assert [(i.policy_name, i.type) for i in world.listed()] == [("silver", "catalog")]


def test_attach_twice_to_one_target_replaces_not_duplicates(world):
    """A second attach finds the target's attachment by its key and replaces its policy, keeping its id."""
    first = world.attach("namespace", ("prod", "sales"), "gold")
    second = world.attach("namespace", ("prod", "sales"), "silver")
    (stored,) = world.attachments.list_all()
    assert first.id == second.id == stored.id.value
    assert stored.policy_id == world.policy_id("silver")


def test_resolve_picks_table_over_namespace_over_catalog(world):
    """With all three attached the table's wins; detached, the namespace's; then the catalog's."""
    world.attach("catalog", ("prod",), "silver")
    namespace = world.attach("namespace", ("prod", "sales"), "gold")
    table = world.attach("table", ("prod", "sales", "eu", "orders"), DEFAULT_POLICY_NAME)
    assert world.resolve_orders().target["type"] == "table"
    world.detach(DEFAULT_POLICY_NAME, table.id)
    assert world.resolve_orders().target == {"type": "namespace", "path": ["prod", "sales"]}
    world.detach("gold", namespace.id)
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
    """Detach by id removes the attachment; detaching the same id again answers NotFoundError."""
    out = world.attach("namespace", ("prod", "sales"), "gold")
    world.detach("gold", out.id)
    assert world.attachments.list_all() == []
    with pytest.raises(NotFoundError, match=rf"^policy gold has no attachment {out.id}$"):
        world.detach("gold", out.id)


@pytest.mark.parametrize("attachment_id", ["x", "da-01m7sd16b1ef2vww335cwcg9k8"])
def test_detach_with_a_malformed_id_is_a_validation_error(world, attachment_id):
    """An id that is not a ``pa-`` id, a discovery ``da-`` id among them, is ValidationError."""
    world.attach("namespace", ("prod", "sales"), "gold")
    with pytest.raises(ValidationError, match="pa-"):
        world.detach("gold", attachment_id)
    assert len(world.attachments.list_all()) == 1


def test_detach_through_an_unknown_policy_is_not_found(world):
    """Detaching through a policy that does not exist is NotFoundError and keeps the attachment."""
    out = world.attach("namespace", ("prod", "sales"), "gold")
    with pytest.raises(NotFoundError, match="^table maintenance policy nope not found$"):
        world.detach("nope", out.id)
    assert len(world.attachments.list_all()) == 1


def test_list_filters_by_policy(world):
    """Listing names one policy and answers only its attachments."""
    world.attach("catalog", ("prod",), "gold")
    world.attach("namespace", ("prod", "sales"), "silver")
    assert [i.path for i in world.listed("silver")] == [("prod", "sales")]


def test_list_for_an_unknown_policy_is_not_found(world):
    """Listing the attachments of a policy that does not exist answers NotFoundError."""
    with pytest.raises(NotFoundError):
        world.list_attachments.execute(ListTableMaintenancePolicyAttachmentsUseCaseInput(policy_name="nope"))


def test_delete_attached_policy_conflicts(world):
    """A policy with an attachment cannot be deleted; detaching frees it."""
    out = world.attach("catalog", ("prod",), "gold")
    service = DeleteTableMaintenancePolicyService(world.policies, world.attachments)
    with pytest.raises(ConflictError):
        service.execute(DeleteTableMaintenancePolicyUseCaseInput(name="gold"))
    world.detach("gold", out.id)
    service.execute(DeleteTableMaintenancePolicyUseCaseInput(name="gold"))


def test_attach_to_catalog_the_gateway_cannot_open_is_404(world):
    """A catalog unknown to the gateway answers NotFoundError for catalog, namespace and table targets."""
    world.gateway.drop_catalog("prod")
    for type_, path in [("catalog", ("prod",)), ("namespace", ("prod", "sales")), ("table", ("prod", "sales", "t"))]:
        with pytest.raises(NotFoundError):
            world.attach(type_, path, "gold")
    assert world.attachments.list_all() == []


def test_attach_to_an_empty_catalog(world):
    """A catalog that holds no table exists, so a policy may be attached to it."""
    world.gateway.add_catalog("empty")
    world.attach("catalog", ("empty",), "gold")
    assert [a.target.path for a in world.attachments.list_all()] == [("empty",)]


def test_attach_to_an_empty_namespace(world):
    """A namespace that holds no table exists, so a policy may be attached to it."""
    world.gateway.add_namespace("prod", "new")
    world.attach("namespace", ("prod", "new"), "gold")
    assert [a.target.path for a in world.attachments.list_all()] == [("prod", "new")]


def test_attach_to_a_missing_namespace_is_not_found(world):
    """A namespace the catalog does not hold is NotFoundError, and nothing is stored."""
    with pytest.raises(NotFoundError, match=r"^namespace prod\.new not found$"):
        world.attach("namespace", ("prod", "new"), "gold")
    assert world.attachments.list_all() == []


def test_attach_to_an_emptied_catalog_and_namespace(world):
    """A catalog or namespace whose tables were all dropped still exists."""
    world.gateway.drop_table("prod", "sales.eu", "orders")
    world.gateway.drop_table("prod", "sales", "customers")
    world.attach("catalog", ("prod",), "gold")
    world.attach("namespace", ("prod", "sales", "eu"), "gold")
    assert len(world.attachments.list_all()) == 2


@pytest.mark.parametrize(
    ("type_", "path"),
    [("catalog", ("secret",)), ("namespace", ("secret", "hr")), ("table", ("secret", "hr", "staff"))],
)
def test_attach_in_a_refused_catalog_is_access_denied(world, type_, path):
    """A catalog the platform's credential cannot read is CatalogAccessDeniedError, and nothing is stored."""
    world.gateway.add_table("secret", "hr", "staff", "u-s")
    world.gateway.deny("secret")
    with pytest.raises(CatalogAccessDeniedError, match="cannot read catalog secret"):
        world.attach(type_, path, "gold")
    assert world.attachments.list_all() == []


def test_detach_of_another_policys_attachment_is_not_found_and_changes_nothing(world):
    """An id that belongs to another policy is NotFoundError: the attachment stays and no table is told."""
    world.register_orders()
    out = world.attach("namespace", ("prod", "sales"), "gold")
    world.changes.calls.clear()
    with pytest.raises(NotFoundError, match=rf"^policy silver has no attachment {out.id}$"):
        world.detach("silver", out.id)
    (stored,) = world.attachments.list_all()
    assert (stored.id.value, stored.policy_id) == (out.id, world.policy_id("gold"))
    assert world.changes.calls == []
    world.detach("gold", out.id)
    assert world.attachments.list_all() == []


def test_detach_wakes_the_tables_whose_policy_changed(world):
    """Detaching tells every managed table whose applicable policy moved."""
    world.register_orders()
    out = world.attach("namespace", ("prod", "sales"), "gold")
    world.changes.calls.clear()
    world.detach("gold", out.id)
    assert [(c.table_uuid, c.change) for c in world.changes.calls] == [("u-1", "policy_changed")]


def test_detach_does_not_read_the_catalog(world):
    """An attachment whose target is gone, or whose catalog the credential cannot read, is still detached."""
    table = world.attach("table", ("prod", "sales", "eu", "orders"), "gold")
    namespace = world.attach("namespace", ("prod", "sales"), "gold")
    world.gateway.drop_table("prod", "sales.eu", "orders")
    world.detach("gold", table.id)
    world.gateway.deny("prod")
    world.detach("gold", namespace.id)
    assert world.attachments.list_all() == []


def _orphaned(world):
    return {(i.type, i.path): i.orphaned for i in world.listed()}


def test_list_marks_attachments_whose_target_left_the_catalog_orphaned(world):
    """An attachment is orphaned once its target no longer exists; an emptied catalog or namespace still does."""
    world.attach("catalog", ("prod",), "gold")
    world.attach("namespace", ("prod", "sales", "eu"), "gold")
    world.attach("namespace", ("prod", "sales"), "silver")
    world.attach("table", ("prod", "sales", "customers"), "gold")
    assert set(_orphaned(world).values()) == {False}
    world.gateway.drop_table("prod", "sales.eu", "orders")
    world.gateway.drop_table("prod", "sales", "customers")
    assert _orphaned(world) == {
        ("catalog", ("prod",)): False,
        ("namespace", ("prod", "sales", "eu")): False,
        ("namespace", ("prod", "sales")): False,
        ("table", ("prod", "sales", "customers")): True,
    }
    world.gateway.drop_namespace("prod", "sales.eu")
    assert _orphaned(world)[("namespace", ("prod", "sales", "eu"))] is True
    assert _orphaned(world)[("namespace", ("prod", "sales"))] is False


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


def test_list_marks_attachments_of_an_unknown_catalog_orphaned(world):
    """A catalog the gateway no longer knows leaves its attachments orphaned instead of failing the list."""
    world.attach("catalog", ("prod",), "gold")
    world.attach("namespace", ("prod", "sales"), "gold")
    world.attach("table", ("prod", "sales", "customers"), "gold")
    world.gateway.drop_catalog("prod")
    assert set(_orphaned(world).values()) == {True}


def test_list_keeps_attachments_in_a_refused_catalog_not_orphaned(world):
    """A catalog the credential cannot read is not known to be gone, so its attachments are not orphaned."""
    world.attach("catalog", ("prod",), "gold")
    world.attach("namespace", ("prod", "sales"), "gold")
    world.attach("table", ("prod", "sales", "customers"), "gold")
    world.gateway.deny("prod")
    assert set(_orphaned(world).values()) == {False}


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
