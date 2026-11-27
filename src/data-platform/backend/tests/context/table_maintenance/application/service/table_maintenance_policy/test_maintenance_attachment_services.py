"""Test the maintenance attach, detach, list and applicable-policy services: a catalog, namespace or table holds it."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from context.table_maintenance.application.domain.model.shared import CatalogId, NamespaceId, TableId
from context.table_maintenance.application.domain.model.table import Table, TableName, TableStatus
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    DEFAULT_POLICY_ID,
    DEFAULT_POLICY_NAME,
    MaintenancePolicyContent,
    TableMaintenancePolicyName,
)
from context.table_maintenance.application.exceptions import (
    ConcurrentUpdateError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from context.table_maintenance.application.port.inbound.table_maintenance_policy import (
    AttachTableMaintenancePolicyUseCaseInput,
    AttachTableMaintenancePolicyUseCaseOutput,
    CreateTableMaintenancePolicyUseCaseInput,
    DeleteTableMaintenancePolicyUseCaseInput,
    DetachTableMaintenancePolicyUseCaseInput,
    DetachTableMaintenancePolicyUseCaseOutput,
    EnsureDefaultTableMaintenancePolicyUseCaseInput,
    ListTableMaintenancePoliciesUseCaseInput,
    ListTableMaintenancePolicyAttachmentsUseCaseInput,
    ResolveApplicableTableMaintenancePolicyUseCaseInput,
    ResolveApplicableTableMaintenancePolicyUseCaseOutput,
)
from context.table_maintenance.application.port.outbound.table import CatalogAccessDeniedError
from context.table_maintenance.application.service.table_maintenance_policy import (
    AttachTableMaintenancePolicyService,
    CreateTableMaintenancePolicyService,
    DeleteTableMaintenancePolicyService,
    DetachTableMaintenancePolicyService,
    EnsureDefaultTableMaintenancePolicyService,
    ListTableMaintenancePoliciesService,
    ListTableMaintenancePolicyAttachmentsService,
    ResolveApplicableTableMaintenancePolicyService,
)
from tests.context.table_maintenance.discovery_decision_samples import MANAGED
from tests.context.table_maintenance.fakes.fake_read_table_metadata_gateway import FakeReadTableMetadataGateway
from tests.context.table_maintenance.fakes.in_memory_catalogs_repo import InMemoryCatalogsRepo
from tests.context.table_maintenance.fakes.in_memory_namespaces_repo import InMemoryNamespacesRepo
from tests.context.table_maintenance.fakes.in_memory_policy_placements_store import InMemoryPolicyPlacementsStore
from tests.context.table_maintenance.fakes.in_memory_table_maintenance_policies_repo import (
    InMemoryTableMaintenancePoliciesRepo,
)
from tests.context.table_maintenance.fakes.in_memory_tables_repo import InMemoryTablesRepo
from tests.context.table_maintenance.fakes.recording_send_table_change_gateway import (
    RecordingSendTableChangeGateway,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.catalog import Catalog
    from context.table_maintenance.application.domain.model.namespace import Namespace

NOW = datetime(2026, 1, 1, tzinfo=UTC)
LATER = datetime(2026, 1, 2, tzinfo=UTC)
CONTENT = MaintenancePolicyContent.platform_default().to_primitives()
ORDERS = ("prod", "sales", "eu", "orders")
ORDERS_NAME = TableName(catalog="prod", namespace="sales.eu", table="orders")


class _World:
    """Run the maintenance policy services on fakes: the default, ``gold`` and ``silver``, and catalog ``prod``.

    ``prod`` holds ``sales.eu.orders`` (uuid ``u-1``) and ``sales.customers`` (uuid ``u-2``), neither of
    which table maintenance knows until a test registers it.
    """

    def __init__(self) -> None:
        self.policies = InMemoryTableMaintenancePoliciesRepo()
        self.catalogs = InMemoryCatalogsRepo()
        self.namespaces = InMemoryNamespacesRepo()
        self.tables = InMemoryTablesRepo()
        self.placements = InMemoryPolicyPlacementsStore(self.catalogs, self.namespaces, self.tables)
        self.gateway = FakeReadTableMetadataGateway()
        self.changes = RecordingSendTableChangeGateway()
        self.now = NOW
        self.gateway.add_table("prod", "sales.eu", "orders", "u-1")
        self.gateway.add_table("prod", "sales", "customers", "u-2")
        EnsureDefaultTableMaintenancePolicyService(self.policies, clock=lambda: NOW).execute(
            EnsureDefaultTableMaintenancePolicyUseCaseInput()
        )
        for name in ("gold", "silver"):
            CreateTableMaintenancePolicyService(self.policies, clock=lambda: NOW).execute(
                CreateTableMaintenancePolicyUseCaseInput(name=name, content=CONTENT)
            )

    def attach(self, policy: str, type_: str, path: tuple[str, ...]) -> AttachTableMaintenancePolicyUseCaseOutput:
        return AttachTableMaintenancePolicyService(
            self.policies,
            self.catalogs,
            self.namespaces,
            self.tables,
            self.gateway,
            self.changes,
            clock=lambda: self.now,
        ).execute(AttachTableMaintenancePolicyUseCaseInput(policy_name=policy, target_type=type_, path=path))

    def detach(self, policy: str, type_: str, path: tuple[str, ...]) -> DetachTableMaintenancePolicyUseCaseOutput:
        return DetachTableMaintenancePolicyService(
            self.policies,
            self.catalogs,
            self.namespaces,
            self.tables,
            self.changes,
            clock=lambda: self.now,
        ).execute(DetachTableMaintenancePolicyUseCaseInput(policy_name=policy, target_type=type_, path=path))

    def listed(self, policy: str) -> list[tuple[str, tuple[str, ...], str | None, str, str, bool]]:
        out = ListTableMaintenancePolicyAttachmentsService(
            self.policies, self.placements, self.gateway, self.tables
        ).execute(ListTableMaintenancePolicyAttachmentsUseCaseInput(policy_name=policy))
        return [(i.type, i.path, i.table_uuid, i.policy_id, i.policy_name, i.orphaned) for i in out.items]

    def resolve(
        self,
        table_uuid: str | None,
        catalog: str | None,
        namespace: str | None = None,
        table: str | None = None,
    ) -> ResolveApplicableTableMaintenancePolicyUseCaseOutput:
        return ResolveApplicableTableMaintenancePolicyService(
            self.policies, self.catalogs, self.namespaces, self.gateway, self.tables
        ).execute(
            ResolveApplicableTableMaintenancePolicyUseCaseInput(
                table_uuid=table_uuid, catalog=catalog, namespace=namespace, table=table
            )
        )

    def resolve_orders(self) -> ResolveApplicableTableMaintenancePolicyUseCaseOutput:
        return self.resolve("u-1", "prod", "sales.eu", "orders")

    def delete(self, name: str) -> None:
        DeleteTableMaintenancePolicyService(self.policies, self.placements).execute(
            DeleteTableMaintenancePolicyUseCaseInput(name=name)
        )

    def register_orders(self, uuid: str = "u-1", now: datetime = NOW) -> None:
        self.tables.create(Table.register(TableId(uuid), ORDERS_NAME, MANAGED, now))

    def policy_id(self, name: str) -> str:
        policy = self.policies.get_by_name(TableMaintenancePolicyName(value=name))
        assert policy is not None
        return policy.id.value

    def stored_catalog(self, name: str = "prod") -> Catalog:
        catalog = self.catalogs.get(CatalogId(name))
        assert catalog is not None
        return catalog

    def stored_namespace(self, *levels: str) -> Namespace:
        namespace = self.namespaces.get(NamespaceId.of("prod", levels))
        assert namespace is not None
        return namespace

    def stored_table(self, uuid: str = "u-1") -> Table:
        table = self.tables.get(TableId(uuid))
        assert table is not None
        return table


@pytest.fixture
def world() -> _World:
    """Provide the maintenance policy services over fakes."""
    return _World()


def _held_ids(world: _World) -> list[str | None]:
    places = [*world.catalogs.list_all(), *world.namespaces.list_all(), *world.tables.list_all()]
    return [None if p.maintenance_policy_id is None else p.maintenance_policy_id.value for p in places]


# --- attach ---


def test_attach_to_a_catalog_seen_for_the_first_time_registers_it(world: _World) -> None:
    """A catalog with no record yet is registered holding the policy; the answer names the place and the policy."""
    out = world.attach("gold", "catalog", ("prod",))

    assert out == AttachTableMaintenancePolicyUseCaseOutput(
        target_type="catalog", path=("prod",), table_uuid=None, policy_id=world.policy_id("gold"), policy_name="gold"
    )
    assert _held_ids(world) == [world.policy_id("gold")]
    assert (world.stored_catalog().version, world.stored_catalog().created_at) == (1, NOW)


def test_attach_to_a_catalog_already_held_replaces_its_policy(world: _World) -> None:
    """Attaching to a catalog that holds another policy replaces it and saves over the record."""
    world.attach("gold", "catalog", ("prod",))
    world.now = LATER

    world.attach("silver", "catalog", ("prod",))

    assert _held_ids(world) == [world.policy_id("silver")]
    assert (world.stored_catalog().version, world.stored_catalog().updated_at) == (2, LATER)
    assert world.listed("gold") == []


def test_attach_to_a_namespace_registers_it(world: _World) -> None:
    """A namespace is held by its catalog and levels."""
    out = world.attach("gold", "namespace", ("prod", "sales", "eu"))

    assert (out.target_type, out.path, out.table_uuid) == ("namespace", ("prod", "sales", "eu"), None)
    held = world.stored_namespace("sales", "eu").maintenance_policy_id
    assert held is not None
    assert held.value == world.policy_id("gold")


def test_attach_to_a_namespace_level_holding_a_dot_is_refused(world: _World) -> None:
    """A table spells its namespace dot-joined, so a policy on a level holding a dot could never apply: 422."""
    world.gateway.add_namespace("prod", "eu.west")

    with pytest.raises(ValidationError, match=r"namespace level 'eu\.west' holds a '\.'"):
        world.attach("gold", "namespace", ("prod", "eu.west"))

    assert world.namespaces.list_all() == []


def test_attach_to_a_table_discovery_never_saw_registers_it_undecided(world: _World) -> None:
    """A table with no record is registered undecided holding the policy, under the uuid the catalog gives it."""
    out = world.attach("gold", "table", ORDERS)

    assert (out.target_type, out.path, out.table_uuid) == ("table", ORDERS, "u-1")
    table = world.stored_table()
    assert (table.status, table.name, table.decided_by) == (TableStatus.UNDECIDED, ORDERS_NAME, None)
    assert table.maintenance_policy_id is not None
    assert table.maintenance_policy_id.value == world.policy_id("gold")
    assert table.discovery_policy_id is None


def test_attach_to_a_known_table_keeps_its_status(world: _World) -> None:
    """A managed table is given the policy and stays managed."""
    world.register_orders()

    world.attach("gold", "table", ORDERS)

    table = world.stored_table()
    assert (table.status, table.version) == (TableStatus.MANAGED, 2)
    assert table.maintenance_policy_id is not None


def test_attach_when_the_table_was_changed_meanwhile_answers_conflict(
    world: _World, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A save from a copy someone else saved over raises ConcurrentUpdateError (409); no table is told."""
    world.register_orders()

    def changed_meanwhile(table: Table) -> Table:
        raise ConcurrentUpdateError(f"table {table.id.value} was changed by someone else")

    monkeypatch.setattr(world.tables, "update", changed_meanwhile)

    with pytest.raises(ConcurrentUpdateError, match="changed by someone else"):
        world.attach("gold", "table", ORDERS)

    assert world.changes.calls == []


def test_the_default_policy_may_be_attached_explicitly(world: _World) -> None:
    """The platform default is a policy like any other: attached to a namespace it overrides the catalog's there."""
    world.attach("gold", "catalog", ("prod",))
    world.attach(DEFAULT_POLICY_NAME, "namespace", ("prod", "sales"))

    out = world.resolve_orders()

    assert (out.policy_id, out.target) == (DEFAULT_POLICY_ID.value, {"type": "namespace", "path": ["prod", "sales"]})


def test_attach_to_an_empty_catalog_and_namespace(world: _World) -> None:
    """A catalog or namespace that holds no table exists, so a policy may be attached to it."""
    world.gateway.add_catalog("empty")
    world.gateway.add_namespace("prod", "new")

    world.attach("gold", "catalog", ("empty",))
    world.attach("gold", "namespace", ("prod", "new"))

    assert world.stored_catalog("empty").maintenance_policy_id is not None
    assert world.stored_namespace("new").maintenance_policy_id is not None


def test_attach_to_a_parent_only_namespace_works_but_a_name_prefix_does_not(world: _World) -> None:
    """A namespace whose tables all sit in child namespaces still exists; a name prefix of it does not."""
    world.gateway.drop_table("prod", "sales", "customers")
    world.attach("gold", "namespace", ("prod", "sales"))

    assert world.resolve_orders().policy_name == "gold"
    with pytest.raises(NotFoundError):
        world.attach("gold", "namespace", ("prod", "sal"))


@pytest.mark.parametrize(
    ("type_", "path"),
    [("catalog", ("nope",)), ("namespace", ("prod", "missing")), ("table", ("prod", "sales", "ghost"))],
)
def test_attach_to_a_missing_place_is_not_found(world: _World, type_: str, path: tuple[str, ...]) -> None:
    """A catalog, namespace or table the catalog does not hold is NotFoundError, and nothing is stored."""
    with pytest.raises(NotFoundError, match="not found"):
        world.attach("gold", type_, path)

    assert _held_ids(world) == []


@pytest.mark.parametrize(
    ("type_", "path"),
    [("catalog", ("prod",)), ("namespace", ("prod", "sales")), ("table", ORDERS)],
)
def test_attach_in_a_refused_catalog_is_access_denied(world: _World, type_: str, path: tuple[str, ...]) -> None:
    """A place in a catalog the credential cannot read raises CatalogAccessDeniedError, and nothing is stored."""
    world.gateway.deny("prod")

    with pytest.raises(CatalogAccessDeniedError, match="cannot read catalog prod"):
        world.attach("gold", type_, path)

    assert _held_ids(world) == []


def test_attach_of_an_unknown_policy_is_not_found(world: _World) -> None:
    """Attaching a policy that does not exist is NotFoundError, and nothing is stored."""
    with pytest.raises(NotFoundError, match="table maintenance policy nope not found"):
        world.attach("nope", "catalog", ("prod",))

    assert _held_ids(world) == []


def test_attach_with_a_bad_target_type_is_a_validation_error(world: _World) -> None:
    """An unknown target type is ValidationError."""
    with pytest.raises(ValidationError):
        world.attach("gold", "warehouse", ("prod",))


# --- detach ---


@pytest.mark.parametrize(
    ("type_", "path"),
    [("catalog", ("prod",)), ("namespace", ("prod", "sales", "eu")), ("table", ORDERS)],
)
def test_detach_lets_go_of_the_policy_and_keeps_the_record(world: _World, type_: str, path: tuple[str, ...]) -> None:
    """Detaching by location clears the place's maintenance policy and keeps its record."""
    world.attach("gold", type_, path)

    world.detach("gold", type_, path)

    assert _held_ids(world) == [None]
    assert world.listed("gold") == []


def test_detach_from_a_table_lets_go_of_the_row_of_that_name_holding_the_policy(world: _World) -> None:
    """A table recreated under the same name leaves two live rows until a scan; the one holding the policy is detached.

    ``u-1`` holds the policy; ``u-2``, recorded later under the same name, holds none and is the latest updated.
    """
    world.attach("gold", "table", ORDERS)
    world.register_orders("u-2", LATER)

    world.detach("gold", "table", ORDERS)

    assert (world.stored_table("u-1").maintenance_policy_id, world.stored_table("u-2").maintenance_policy_id) == (
        None,
        None,
    )
    assert world.stored_table("u-2").version == 1


def test_detach_from_a_table_whose_live_rows_hold_another_policy_is_not_found(world: _World) -> None:
    """When no live row of the name holds the policy, the latest updated one answers that it is not attached."""
    world.attach("silver", "table", ORDERS)
    world.register_orders("u-2", LATER)

    with pytest.raises(NotFoundError, match=r"maintenance policy mp-\w+ is not attached to table"):
        world.detach("gold", "table", ORDERS)

    assert world.stored_table("u-1").maintenance_policy_id is not None


def test_detach_of_another_policy_is_not_found_and_tells_no_table(world: _World) -> None:
    """A place holding another policy is not this policy's to detach; it keeps what it holds and no table is told."""
    world.register_orders()
    world.attach("gold", "namespace", ("prod", "sales"))
    world.changes.calls.clear()

    with pytest.raises(NotFoundError, match=r"maintenance policy mp-\w+ is not attached to namespace"):
        world.detach("silver", "namespace", ("prod", "sales"))

    held = world.stored_namespace("sales").maintenance_policy_id
    assert held is not None
    assert held.value == world.policy_id("gold")
    assert world.changes.calls == []


@pytest.mark.parametrize(
    ("type_", "path"),
    [("catalog", ("prod",)), ("namespace", ("prod", "sales")), ("table", ORDERS)],
)
def test_detach_from_a_place_with_no_record_is_not_found(world: _World, type_: str, path: tuple[str, ...]) -> None:
    """A place table maintenance holds nothing for is NotFoundError."""
    with pytest.raises(NotFoundError, match="not found"):
        world.detach("gold", type_, path)


def test_detach_twice_is_not_found_the_second_time(world: _World) -> None:
    """Once detached, the place no longer holds the policy."""
    world.attach("gold", "namespace", ("prod", "sales"))
    world.detach("gold", "namespace", ("prod", "sales"))

    with pytest.raises(NotFoundError, match="is not attached"):
        world.detach("gold", "namespace", ("prod", "sales"))


def test_detach_does_not_read_the_catalog(world: _World) -> None:
    """Detaching reads no catalog, so a place whose catalog is gone or refused is detached the same way."""
    world.attach("gold", "namespace", ("prod", "sales"))
    world.attach("gold", "table", ORDERS)
    world.gateway.drop_table("prod", "sales.eu", "orders")
    world.gateway.deny("prod")
    reads = len(world.gateway.calls)

    world.detach("gold", "namespace", ("prod", "sales"))
    world.detach("gold", "table", ORDERS)

    assert _held_ids(world) == [None, None]
    assert len(world.gateway.calls) == reads


def test_detach_through_an_unknown_policy_is_not_found(world: _World) -> None:
    """Detaching through a policy that does not exist is NotFoundError and keeps what is held."""
    world.attach("gold", "catalog", ("prod",))

    with pytest.raises(NotFoundError, match="^table maintenance policy nope not found$"):
        world.detach("nope", "catalog", ("prod",))

    assert _held_ids(world) == [world.policy_id("gold")]


def test_detach_with_a_bad_target_is_a_validation_error(world: _World) -> None:
    """An unknown target type, or a path that names no place of its type, is ValidationError."""
    with pytest.raises(ValidationError):
        world.detach("gold", "warehouse", ("prod",))
    with pytest.raises(ValidationError):
        world.detach("gold", "table", ("prod", "orders"))


def test_detach_when_the_place_was_changed_meanwhile_answers_conflict(
    world: _World, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A detach saved from a copy someone else saved over raises ConcurrentUpdateError; no table is told."""
    world.register_orders()
    world.attach("gold", "catalog", ("prod",))
    world.changes.calls.clear()

    def changed_meanwhile(catalog: Catalog) -> Catalog:
        raise ConcurrentUpdateError(f"catalog {catalog.id.value} was changed by someone else")

    monkeypatch.setattr(world.catalogs, "update", changed_meanwhile)

    with pytest.raises(ConcurrentUpdateError):
        world.detach("gold", "catalog", ("prod",))

    assert world.changes.calls == []


def test_detach_tells_the_tables_whose_policy_changed(world: _World) -> None:
    """Detaching tells every managed table whose applicable policy moved."""
    world.register_orders()
    world.attach("gold", "namespace", ("prod", "sales"))
    world.changes.calls.clear()

    world.detach("gold", "namespace", ("prod", "sales"))

    assert [(c.table_uuid, c.change) for c in world.changes.calls] == [("u-1", "policy_changed")]


# --- list ---


def test_list_carries_each_place(world: _World) -> None:
    """Each listed place carries its target, the policy and whether it is gone, by type and then path."""
    world.attach("gold", "table", ORDERS)
    world.attach("gold", "catalog", ("prod",))
    gold = world.policy_id("gold")

    assert world.listed("gold") == [
        ("catalog", ("prod",), None, gold, "gold", False),
        ("table", ORDERS, "u-1", gold, "gold", False),
    ]


def test_list_shows_only_the_policys_places(world: _World) -> None:
    """Another policy's places are not listed."""
    world.attach("gold", "catalog", ("prod",))
    world.attach("silver", "namespace", ("prod", "sales"))

    assert [item[1] for item in world.listed("silver")] == [("prod", "sales")]


def test_list_marks_a_place_that_left_the_catalog_orphaned(world: _World) -> None:
    """A namespace no longer in the catalog is orphaned; a catalog that still exists is not."""
    world.attach("gold", "catalog", ("prod",))
    world.attach("gold", "namespace", ("prod", "sales", "eu"))
    world.gateway.drop_namespace("prod", "sales.eu")

    assert [(item[0], item[5]) for item in world.listed("gold")] == [("catalog", False), ("namespace", True)]


def test_list_in_a_refused_catalog_is_not_orphaned(world: _World) -> None:
    """A catalog the credential cannot read is not known to be gone: its places are listed, none orphaned."""
    world.attach("gold", "catalog", ("prod",))
    world.attach("gold", "namespace", ("prod", "sales"))
    world.gateway.deny("prod")

    assert [item[5] for item in world.listed("gold")] == [False, False]


def test_list_of_an_unknown_policy_is_not_found(world: _World) -> None:
    """Listing the places of a policy that does not exist is NotFoundError."""
    with pytest.raises(NotFoundError, match="table maintenance policy nope not found"):
        world.listed("nope")


def test_list_policies_counts_the_places_each_is_attached_to(world: _World) -> None:
    """Each listed policy carries how many places hold it."""
    world.attach("gold", "catalog", ("prod",))
    world.attach("gold", "namespace", ("prod", "sales"))

    listed = ListTableMaintenancePoliciesService(world.policies, world.placements).execute(
        ListTableMaintenancePoliciesUseCaseInput()
    )

    assert {i.name: i.attachment_count for i in listed.items} == {DEFAULT_POLICY_NAME: 0, "gold": 2, "silver": 0}


# --- delete ---


def test_deleting_a_policy_still_attached_is_refused_with_the_places(world: _World) -> None:
    """A policy any place holds cannot be deleted: the refusal names each place, and the policy stays."""
    world.attach("gold", "table", ORDERS)
    world.attach("gold", "namespace", ("prod", "sales"))
    world.attach("gold", "catalog", ("prod",))

    with pytest.raises(
        ConflictError,
        match=(
            r"^maintenance policy gold is still attached to "
            r"catalog:prod, namespace:prod\.sales, table:prod\.sales\.eu\.orders$"
        ),
    ):
        world.delete("gold")

    assert world.policies.get_by_name(TableMaintenancePolicyName(value="gold")) is not None


def test_a_policy_detached_everywhere_may_be_deleted(world: _World) -> None:
    """Detaching frees the policy, which may then be deleted."""
    world.attach("gold", "catalog", ("prod",))
    world.detach("gold", "catalog", ("prod",))

    world.delete("gold")

    assert world.policies.get_by_name(TableMaintenancePolicyName(value="gold")) is None


def test_the_default_policy_cannot_be_deleted(world: _World) -> None:
    """The platform default is refused whether or not anything holds it."""
    with pytest.raises(ConflictError, match="^the default policy cannot be deleted$"):
        world.delete(DEFAULT_POLICY_NAME)


# --- resolve ---


def test_nothing_attached_falls_back_to_the_default(world: _World) -> None:
    """With nothing attached the platform default applies, from no place."""
    out = world.resolve_orders()

    assert (out.policy_id, out.policy_name, out.version, out.target) == (
        DEFAULT_POLICY_ID.value,
        DEFAULT_POLICY_NAME,
        1,
        None,
    )


def test_a_table_policy_beats_a_namespace_policy(world: _World) -> None:
    """The policy the table holds wins over its namespace's."""
    world.register_orders()
    world.attach("gold", "namespace", ("prod", "sales"))
    world.attach("silver", "table", ORDERS)

    out = world.resolve_orders()

    assert (out.policy_name, out.target) == ("silver", {"type": "table", "path": list(ORDERS), "table_uuid": "u-1"})


def test_the_deepest_namespace_beats_its_parent_and_the_catalog(world: _World) -> None:
    """A namespace's policy beats the one above it and the catalog's for a table below both."""
    world.attach("silver", "catalog", ("prod",))
    world.attach("gold", "namespace", ("prod", "sales"))

    out = world.resolve_orders()

    assert (out.policy_id, out.policy_name) == (world.policy_id("gold"), "gold")
    assert out.target == {"type": "namespace", "path": ["prod", "sales"]}


def test_resolve_picks_table_then_namespace_then_catalog_as_each_is_detached(world: _World) -> None:
    """With all three attached the table's wins; detached, the namespace's; then the catalog's."""
    world.attach("silver", "catalog", ("prod",))
    world.attach("gold", "namespace", ("prod", "sales"))
    world.attach(DEFAULT_POLICY_NAME, "table", ORDERS)
    assert world.resolve_orders().target == {"type": "table", "path": list(ORDERS), "table_uuid": "u-1"}

    world.detach(DEFAULT_POLICY_NAME, "table", ORDERS)
    assert world.resolve_orders().target == {"type": "namespace", "path": ["prod", "sales"]}

    world.detach("gold", "namespace", ("prod", "sales"))
    assert (world.resolve_orders().policy_name, world.resolve_orders().target) == (
        "silver",
        {"type": "catalog", "path": ["prod"]},
    )


def test_a_renamed_table_keeps_its_own_policy_and_takes_its_new_namespaces(world: _World) -> None:
    """The table's policy follows its uuid; namespace policies follow the name the catalog gives it now."""
    world.attach("silver", "table", ORDERS)
    world.attach("gold", "namespace", ("prod", "sales"))
    world.gateway.add_table("prod", "archive", "orders_old", "u-9")
    world.attach("gold", "namespace", ("prod", "archive"))
    world.gateway.drop_table("prod", "sales.eu", "orders")
    world.gateway.add_table("prod", "archive", "orders_renamed", "u-1")
    world.gateway.add_table("prod", "archive", "other", "u-3")

    assert world.resolve("u-1", "prod", "archive", "orders_renamed").policy_name == "silver"
    assert world.resolve("u-3", "prod", "archive", "other").target == {"type": "namespace", "path": ["prod", "archive"]}


def test_resolve_for_a_namespace_starts_at_that_namespace(world: _World) -> None:
    """A namespace query ignores table policies below it and starts at the namespace."""
    world.attach("silver", "catalog", ("prod",))
    world.attach("gold", "table", ORDERS)

    out = world.resolve(None, "prod", "sales.eu")

    assert (out.policy_name, out.target) == ("silver", {"type": "catalog", "path": ["prod"]})


def test_resolve_by_table_name_looks_up_the_uuid(world: _World) -> None:
    """Without a uuid the table's uuid is read from the catalog, and the policy it holds applies."""
    world.attach("gold", "table", ORDERS)

    assert world.resolve(None, "prod", "sales.eu", "orders").policy_name == "gold"


def test_resolve_by_uuid_alone_reads_the_recorded_table(world: _World) -> None:
    """A known table's uuid is enough: its name comes from its record; an unknown uuid is NotFoundError."""
    world.register_orders()
    world.attach("gold", "namespace", ("prod", "sales"))

    out = world.resolve("u-1", None)

    assert (out.policy_name, out.target) == ("gold", {"type": "namespace", "path": ["prod", "sales"]})
    with pytest.raises(NotFoundError):
        world.resolve("u-unknown", None)


def test_resolve_reads_only_the_namespaces_enclosing_the_place(world: _World) -> None:
    """A policy on a sibling namespace does not apply."""
    world.attach("gold", "namespace", ("prod", "sales"))
    world.gateway.add_namespace("prod", "sales.us")
    world.attach("silver", "namespace", ("prod", "sales", "us"))

    assert world.resolve_orders().policy_name == "gold"
