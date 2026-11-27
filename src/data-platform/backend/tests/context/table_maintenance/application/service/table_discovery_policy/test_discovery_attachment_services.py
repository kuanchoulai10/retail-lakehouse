"""Test the attach, detach and list services: a discovery policy is held by a catalog, namespace or table."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from context.table_maintenance.application.domain.model.shared import CatalogId, NamespaceId, TableId
from context.table_maintenance.application.domain.model.table import Table, TableName, TableStatus
from context.table_maintenance.application.domain.model.table_discovery_policy import TableDiscoveryPolicyName
from context.table_maintenance.application.exceptions import ConcurrentUpdateError, NotFoundError, ValidationError
from context.table_maintenance.application.port.inbound.table_discovery_policy import (
    AttachTableDiscoveryPolicyUseCaseInput,
    AttachTableDiscoveryPolicyUseCaseOutput,
    CreateTableDiscoveryPolicyUseCaseInput,
    DetachTableDiscoveryPolicyUseCaseInput,
    DetachTableDiscoveryPolicyUseCaseOutput,
    ListTableDiscoveryPolicyAttachmentsUseCaseInput,
    ListTableDiscoveryPolicyAttachmentsUseCaseOutput,
)
from context.table_maintenance.application.port.outbound.table import (
    CatalogAccessDeniedError,
    SendDiscoveryRequestGatewayInput,
)
from context.table_maintenance.application.service.table_discovery_policy import (
    AttachTableDiscoveryPolicyService,
    CreateTableDiscoveryPolicyService,
    DetachTableDiscoveryPolicyService,
    ListTableDiscoveryPolicyAttachmentsService,
)
from tests.context.table_maintenance.discovery_decision_samples import MANAGED
from tests.context.table_maintenance.fakes.fake_read_table_metadata_gateway import FakeReadTableMetadataGateway
from tests.context.table_maintenance.fakes.in_memory_catalogs_repo import InMemoryCatalogsRepo
from tests.context.table_maintenance.fakes.in_memory_namespaces_repo import InMemoryNamespacesRepo
from tests.context.table_maintenance.fakes.in_memory_policy_placements_store import InMemoryPolicyPlacementsStore
from tests.context.table_maintenance.fakes.in_memory_table_discovery_policies_repo import (
    InMemoryTableDiscoveryPoliciesRepo,
)
from tests.context.table_maintenance.fakes.in_memory_tables_repo import InMemoryTablesRepo
from tests.context.table_maintenance.fakes.recording_send_discovery_request_gateway import (
    RecordingSendDiscoveryRequestGateway,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.catalog import Catalog
    from context.table_maintenance.application.domain.model.namespace import Namespace

NOW = datetime(2026, 11, 1, tzinfo=UTC)
LATER = datetime(2026, 11, 2, tzinfo=UTC)
RULES = ({"action": "include", "table_name_pattern": "orders_*"},)
ORDERS = ("iceberg", "sales", "eu", "orders")
ORDERS_NAME = TableName(catalog="iceberg", namespace="sales.eu", table="orders")


class _World:
    """Run the attachment services on fakes: policies ``mine`` and ``other``, and catalog ``iceberg``.

    ``iceberg`` holds the table ``sales.eu.orders`` (uuid ``u-1``), which table maintenance does not know.
    Change ids run ``c1``, ``c2``, and so on.
    """

    def __init__(self) -> None:
        self.policies = InMemoryTableDiscoveryPoliciesRepo()
        self.catalogs = InMemoryCatalogsRepo()
        self.namespaces = InMemoryNamespacesRepo()
        self.tables = InMemoryTablesRepo()
        self.placements = InMemoryPolicyPlacementsStore(self.catalogs, self.namespaces, self.tables)
        self.catalog = FakeReadTableMetadataGateway()
        self.requests = RecordingSendDiscoveryRequestGateway()
        self.now = NOW
        self._changes = iter(f"c{n}" for n in range(1, 100))
        self.catalog.add_table("iceberg", "sales.eu", "orders", "u-1")
        for name in ("mine", "other"):
            CreateTableDiscoveryPolicyService(self.policies, clock=lambda: NOW).execute(
                CreateTableDiscoveryPolicyUseCaseInput(name=name, description="", rules=RULES)
            )

    def attach(self, policy: str, type_: str, path: tuple[str, ...]) -> AttachTableDiscoveryPolicyUseCaseOutput:
        return AttachTableDiscoveryPolicyService(
            self.policies,
            self.catalogs,
            self.namespaces,
            self.tables,
            self.catalog,
            self.requests,
            clock=lambda: self.now,
            new_change_id=lambda: next(self._changes),
        ).execute(AttachTableDiscoveryPolicyUseCaseInput(policy_name=policy, target_type=type_, path=path))

    def detach(self, policy: str, type_: str, path: tuple[str, ...]) -> DetachTableDiscoveryPolicyUseCaseOutput:
        return DetachTableDiscoveryPolicyService(
            self.policies,
            self.catalogs,
            self.namespaces,
            self.tables,
            self.requests,
            clock=lambda: self.now,
            new_change_id=lambda: next(self._changes),
        ).execute(DetachTableDiscoveryPolicyUseCaseInput(policy_name=policy, target_type=type_, path=path))

    def list(self, policy: str) -> ListTableDiscoveryPolicyAttachmentsUseCaseOutput:
        return ListTableDiscoveryPolicyAttachmentsService(
            self.policies, self.placements, self.catalog, self.tables
        ).execute(ListTableDiscoveryPolicyAttachmentsUseCaseInput(policy_name=policy))

    def policy_id(self, name: str) -> str:
        policy = self.policies.get_by_name(TableDiscoveryPolicyName(value=name))
        assert policy is not None
        return policy.id.value

    def stored_catalog(self, name: str = "iceberg") -> Catalog:
        catalog = self.catalogs.get(CatalogId(name))
        assert catalog is not None
        return catalog

    def stored_namespace(self, *levels: str) -> Namespace:
        namespace = self.namespaces.get(NamespaceId.of("iceberg", levels))
        assert namespace is not None
        return namespace

    def stored_table(self, uuid: str = "u-1") -> Table:
        table = self.tables.get(TableId(uuid))
        assert table is not None
        return table


@pytest.fixture
def world() -> _World:
    """Provide the attachment services over fakes."""
    return _World()


def _held_ids(world: _World) -> list[str | None]:
    places = [*world.catalogs.list_all(), *world.namespaces.list_all(), *world.tables.list_all()]
    return [None if p.discovery_policy_id is None else p.discovery_policy_id.value for p in places]


# --- attach ---


def test_attach_to_a_catalog_seen_for_the_first_time_registers_it(world: _World) -> None:
    """A catalog with no record yet is registered holding the policy, and its whole catalog is scanned."""
    out = world.attach("mine", "catalog", ("iceberg",))

    assert out == AttachTableDiscoveryPolicyUseCaseOutput(
        target_type="catalog", path=("iceberg",), table_uuid=None, policy_id=world.policy_id("mine"), policy_name="mine"
    )
    assert _held_ids(world) == [world.policy_id("mine")]
    assert (world.stored_catalog().version, world.stored_catalog().created_at) == (1, NOW)
    assert world.requests.calls == [SendDiscoveryRequestGatewayInput("iceberg", None, change_id="c1")]


def test_attach_to_a_catalog_already_held_replaces_its_policy(world: _World) -> None:
    """Attaching to a catalog that holds another policy replaces it and saves over the record."""
    world.attach("mine", "catalog", ("iceberg",))
    world.now = LATER

    world.attach("other", "catalog", ("iceberg",))

    assert _held_ids(world) == [world.policy_id("other")]
    assert (world.stored_catalog().version, world.stored_catalog().updated_at) == (2, LATER)
    assert world.list("mine").items == ()


def test_attach_to_a_namespace_registers_it_and_scans_the_namespace(world: _World) -> None:
    """A namespace is held by its catalog and levels, and only that namespace is scanned."""
    out = world.attach("mine", "namespace", ("iceberg", "sales", "eu"))

    assert (out.target_type, out.path, out.table_uuid) == ("namespace", ("iceberg", "sales", "eu"), None)
    assert world.stored_namespace("sales", "eu").discovery_policy_id is not None
    assert world.requests.calls == [SendDiscoveryRequestGatewayInput("iceberg", "sales.eu", change_id="c1")]


def test_attach_to_a_namespace_level_holding_a_dot_is_refused(world: _World) -> None:
    """A table spells its namespace dot-joined, so a policy on a level holding a dot could never apply: 422."""
    world.catalog.add_namespace("iceberg", "eu.west")

    with pytest.raises(ValidationError, match=r"namespace level 'eu\.west' holds a '\.'"):
        world.attach("mine", "namespace", ("iceberg", "eu.west"))

    assert world.namespaces.list_all() == []
    assert world.requests.calls == []


def test_attach_to_a_table_discovery_never_saw_registers_it_undecided_and_requests_a_scan(world: _World) -> None:
    """A table with no record is registered undecided holding the policy, and its namespace is scanned at once."""
    out = world.attach("mine", "table", ORDERS)

    assert (out.target_type, out.path, out.table_uuid) == ("table", ORDERS, "u-1")
    table = world.stored_table()
    assert (table.status, table.name, table.decided_by) == (TableStatus.UNDECIDED, ORDERS_NAME, None)
    assert table.discovery_policy_id is not None
    assert table.discovery_policy_id.value == world.policy_id("mine")
    assert world.requests.calls == [SendDiscoveryRequestGatewayInput("iceberg", "sales.eu", change_id="c1")]


def test_attach_to_a_known_table_keeps_its_status(world: _World) -> None:
    """A managed table is given the policy and stays managed until the scan decides it again."""
    world.tables.create(Table.register(TableId("u-1"), ORDERS_NAME, MANAGED, NOW))

    world.attach("mine", "table", ORDERS)

    table = world.stored_table()
    assert (table.status, table.version) == (TableStatus.MANAGED, 2)
    assert table.discovery_policy_id is not None


def test_attach_when_the_table_was_changed_meanwhile_answers_conflict(
    world: _World, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A save from a copy someone else saved over raises ConcurrentUpdateError (409); nothing is scanned."""
    world.tables.create(Table.register(TableId("u-1"), ORDERS_NAME, MANAGED, NOW))

    def changed_meanwhile(table: Table) -> Table:
        raise ConcurrentUpdateError(f"table {table.id.value} was changed by someone else")

    monkeypatch.setattr(world.tables, "update", changed_meanwhile)

    with pytest.raises(ConcurrentUpdateError, match="changed by someone else"):
        world.attach("mine", "table", ORDERS)

    assert world.requests.calls == []


def test_a_failed_scan_request_still_saves_the_attach(world: _World, caplog: pytest.LogCaptureFixture) -> None:
    """The scan is best effort: a request that cannot be sent is logged, and the attach stands."""
    world.requests.failing.add("iceberg")

    with caplog.at_level(logging.ERROR):
        out = world.attach("mine", "catalog", ("iceberg",))

    assert out.policy_name == "mine"
    assert world.stored_catalog().discovery_policy_id is not None
    assert "could not request a discovery of catalog iceberg" in caplog.text


def test_attach_to_an_empty_catalog(world: _World) -> None:
    """A catalog that holds nothing yet may be attached to."""
    world.catalog.add_catalog("fresh")

    world.attach("mine", "catalog", ("fresh",))

    assert world.stored_catalog("fresh").discovery_policy_id is not None


def test_attach_to_a_missing_namespace_is_not_found(world: _World) -> None:
    """A namespace the catalog does not hold is NotFoundError, and nothing is stored."""
    with pytest.raises(NotFoundError, match=r"namespace iceberg\.ghost not found"):
        world.attach("mine", "namespace", ("iceberg", "ghost"))

    assert world.namespaces.list_all() == []


@pytest.mark.parametrize(
    ("type_", "path"),
    [("catalog", ("nope",)), ("table", ("iceberg", "sales", "eu", "ghost"))],
)
def test_attach_to_a_missing_catalog_or_table_is_not_found(world: _World, type_: str, path: tuple[str, ...]) -> None:
    """A catalog or table the catalog does not hold is NotFoundError, and nothing is stored."""
    with pytest.raises(NotFoundError, match="not found"):
        world.attach("mine", type_, path)

    assert _held_ids(world) == []


@pytest.mark.parametrize(
    ("type_", "path"),
    [("catalog", ("iceberg",)), ("namespace", ("iceberg", "sales")), ("table", ORDERS)],
)
def test_attach_in_a_refused_catalog_is_access_denied(world: _World, type_: str, path: tuple[str, ...]) -> None:
    """A target in a catalog the credential cannot read raises CatalogAccessDeniedError, and nothing is stored."""
    world.catalog.deny("iceberg")

    with pytest.raises(CatalogAccessDeniedError, match="cannot read catalog iceberg"):
        world.attach("mine", type_, path)

    assert _held_ids(world) == []


def test_attach_of_an_unknown_policy_is_not_found(world: _World) -> None:
    """Attaching a policy that does not exist is NotFoundError, and nothing is stored."""
    with pytest.raises(NotFoundError, match="discovery policy ghost not found"):
        world.attach("ghost", "catalog", ("iceberg",))

    assert _held_ids(world) == []


def test_attach_with_a_bad_target_type_is_a_validation_error(world: _World) -> None:
    """An unknown target type is ValidationError."""
    with pytest.raises(ValidationError):
        world.attach("mine", "warehouse", ("iceberg",))


# --- detach ---


@pytest.mark.parametrize(
    ("type_", "path"),
    [("catalog", ("iceberg",)), ("namespace", ("iceberg", "sales", "eu")), ("table", ORDERS)],
)
def test_detach_lets_go_of_the_policy_and_scans_again(world: _World, type_: str, path: tuple[str, ...]) -> None:
    """Detaching clears the place's discovery policy, keeps its record, and scans what it covered."""
    world.attach("mine", type_, path)

    world.detach("mine", type_, path)

    assert _held_ids(world) == [None]
    scope = None if type_ == "catalog" else "sales.eu"
    assert world.requests.calls[-1] == SendDiscoveryRequestGatewayInput("iceberg", scope, change_id="c2")


def test_detach_from_a_table_lets_go_of_the_row_of_that_name_holding_the_policy(world: _World) -> None:
    """A table recreated under the same name leaves two live rows until a scan; the one holding the policy is detached.

    ``u-1`` holds the policy; ``u-2``, recorded later under the same name, holds none and is the latest updated.
    """
    world.attach("mine", "table", ORDERS)
    world.tables.create(Table.register(TableId("u-2"), ORDERS_NAME, MANAGED, LATER))

    world.detach("mine", "table", ORDERS)

    assert (world.stored_table("u-1").discovery_policy_id, world.stored_table("u-2").discovery_policy_id) == (
        None,
        None,
    )
    assert world.stored_table("u-2").version == 1
    assert world.requests.calls[-1] == SendDiscoveryRequestGatewayInput("iceberg", "sales.eu", change_id="c2")


def test_detach_from_a_table_whose_live_rows_hold_another_policy_is_not_found(world: _World) -> None:
    """When no live row of the name holds the policy, the latest updated one answers that it is not attached."""
    world.attach("other", "table", ORDERS)
    world.tables.create(Table.register(TableId("u-2"), ORDERS_NAME, MANAGED, LATER))

    with pytest.raises(NotFoundError, match=r"discovery policy dp-\w+ is not attached to table"):
        world.detach("mine", "table", ORDERS)

    assert world.stored_table("u-1").discovery_policy_id is not None


def test_detach_of_another_policy_is_not_found(world: _World) -> None:
    """A place holding another policy is not this policy's to detach; it keeps what it holds."""
    world.attach("other", "catalog", ("iceberg",))

    with pytest.raises(NotFoundError, match=r"discovery policy dp-\w+ is not attached to catalog iceberg"):
        world.detach("mine", "catalog", ("iceberg",))

    assert world.stored_catalog().discovery_policy_id is not None
    assert len(world.requests.calls) == 1


@pytest.mark.parametrize(
    ("type_", "path"),
    [("catalog", ("iceberg",)), ("namespace", ("iceberg", "sales")), ("table", ORDERS)],
)
def test_detach_from_a_place_with_no_record_is_not_found(world: _World, type_: str, path: tuple[str, ...]) -> None:
    """A place table maintenance holds nothing for is NotFoundError."""
    with pytest.raises(NotFoundError, match="not found"):
        world.detach("mine", type_, path)


def test_detach_does_not_read_the_catalog(world: _World) -> None:
    """Detaching reads no catalog, so a place whose catalog is gone or refused is detached the same way."""
    world.attach("mine", "namespace", ("iceberg", "sales"))
    world.attach("mine", "table", ORDERS)
    world.catalog.deny("iceberg")
    reads = len(world.catalog.calls)

    world.detach("mine", "namespace", ("iceberg", "sales"))
    world.detach("mine", "table", ORDERS)

    assert _held_ids(world) == [None, None]
    assert len(world.catalog.calls) == reads


def test_detach_from_an_unknown_policy_is_not_found(world: _World) -> None:
    """Detaching a policy that does not exist is NotFoundError."""
    world.attach("mine", "catalog", ("iceberg",))

    with pytest.raises(NotFoundError, match="discovery policy ghost not found"):
        world.detach("ghost", "catalog", ("iceberg",))


def test_detach_with_a_bad_target_is_a_validation_error(world: _World) -> None:
    """An unknown target type, or a path that names no place of its type, is ValidationError."""
    with pytest.raises(ValidationError):
        world.detach("mine", "warehouse", ("iceberg",))
    with pytest.raises(ValidationError):
        world.detach("mine", "table", ("iceberg", "orders"))


def test_a_failed_scan_request_still_saves_the_detach(world: _World) -> None:
    """A detach whose scan cannot be requested still lets go of the policy."""
    world.attach("mine", "catalog", ("iceberg",))
    world.requests.failing.add("iceberg")

    world.detach("mine", "catalog", ("iceberg",))

    assert world.stored_catalog().discovery_policy_id is None


# --- list ---


def test_list_carries_each_place(world: _World) -> None:
    """Each listed place carries its target, the policy and whether it is gone, by type and then path."""
    world.attach("mine", "table", ORDERS)
    world.attach("mine", "catalog", ("iceberg",))

    items = world.list("mine").items

    assert [(i.type, i.path, i.table_uuid, i.policy_id, i.policy_name, i.orphaned) for i in items] == [
        ("catalog", ("iceberg",), None, world.policy_id("mine"), "mine", False),
        ("table", ORDERS, "u-1", world.policy_id("mine"), "mine", False),
    ]


def test_list_marks_a_place_that_left_the_catalog_orphaned(world: _World) -> None:
    """A namespace no longer in the catalog is orphaned; a catalog that still exists is not."""
    world.attach("mine", "catalog", ("iceberg",))
    world.attach("mine", "namespace", ("iceberg", "sales", "eu"))
    world.catalog.drop_namespace("iceberg", "sales.eu")

    listed = [(item.type, item.orphaned) for item in world.list("mine").items]

    assert listed == [("catalog", False), ("namespace", True)]


def test_list_in_a_refused_catalog_is_not_orphaned(world: _World) -> None:
    """A catalog the credential cannot read is not known to be gone: its places are listed, none orphaned."""
    world.attach("mine", "catalog", ("iceberg",))
    world.attach("mine", "namespace", ("iceberg", "sales"))
    world.catalog.deny("iceberg")

    assert [item.orphaned for item in world.list("mine").items] == [False, False]


def test_list_shows_only_the_policys_places(world: _World) -> None:
    """Another policy's places are not listed."""
    world.attach("other", "catalog", ("iceberg",))
    world.attach("mine", "namespace", ("iceberg", "sales"))

    assert [item.path for item in world.list("mine").items] == [("iceberg", "sales")]


def test_list_of_an_unknown_policy_is_not_found(world: _World) -> None:
    """Listing the places of a policy that does not exist is NotFoundError."""
    with pytest.raises(NotFoundError, match="discovery policy ghost not found"):
        world.list("ghost")
