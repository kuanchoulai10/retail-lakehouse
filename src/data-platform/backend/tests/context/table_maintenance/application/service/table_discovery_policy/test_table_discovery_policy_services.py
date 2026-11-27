"""Test the discovery policy use case services."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from context.table_maintenance.application.domain.model.catalog import Catalog
from context.table_maintenance.application.domain.model.namespace import Namespace
from context.table_maintenance.application.domain.model.shared import (
    CatalogId,
    NamespaceId,
    TableDiscoveryPolicyId,
    TableId,
)
from context.table_maintenance.application.domain.model.table import Table, TableName
from context.table_maintenance.application.domain.model.table_discovery_policy import TableDiscoveryPolicyName
from context.table_maintenance.application.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy import (
    CreateTableDiscoveryPolicyUseCaseInput,
    CreateTableDiscoveryPolicyUseCaseOutput,
    DeleteTableDiscoveryPolicyUseCaseInput,
    GetTableDiscoveryPolicyUseCaseInput,
    GetTableDiscoveryPolicyUseCaseOutput,
    GetTableDiscoveryPolicyVersionUseCaseInput,
    GetTableDiscoveryPolicyVersionUseCaseOutput,
    ListTableDiscoveryPoliciesUseCaseInput,
    ListTableDiscoveryPoliciesUseCaseOutput,
    UpdateTableDiscoveryPolicyUseCaseInput,
    UpdateTableDiscoveryPolicyUseCaseOutput,
)
from context.table_maintenance.application.service.table_discovery_policy import (
    CreateTableDiscoveryPolicyService,
    DeleteTableDiscoveryPolicyService,
    GetTableDiscoveryPolicyService,
    GetTableDiscoveryPolicyVersionService,
    ListTableDiscoveryPoliciesService,
    UpdateTableDiscoveryPolicyService,
)
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
from tests.context.table_maintenance.id_shape import IdShape

NOW = datetime(2026, 11, 1, tzinfo=UTC)
LATER = datetime(2026, 11, 2, tzinfo=UTC)
DP_ID = IdShape(TableDiscoveryPolicyId)


def _rule(action: str, pattern: str) -> dict[str, str]:
    return {"action": action, "table_name_pattern": pattern}


INCLUDE_ORDERS = (_rule("include", "orders_*"),)
INCLUDE_ALL_BUT_TMP = (_rule("include", "*"), _rule("exclude", "*_tmp"))


class ServiceWorld:
    """Run the discovery policy services on in-memory fakes that start empty."""

    def __init__(self) -> None:
        """Start with no policy.

        The policies fake is not linked to the placements, so it deletes an attached policy freely and
        only the delete service's own check refuses it. The placements are read from the catalogs,
        namespaces and tables fakes, as the SQL store reads their rows.
        """
        self.catalogs = InMemoryCatalogsRepo()
        self.namespaces = InMemoryNamespacesRepo()
        self.tables = InMemoryTablesRepo()
        self.placements = InMemoryPolicyPlacementsStore(self.catalogs, self.namespaces, self.tables)
        self.policies = InMemoryTableDiscoveryPoliciesRepo()
        self.requests = RecordingSendDiscoveryRequestGateway()
        self.change_ids = iter(f"c{n}" for n in range(1, 100))
        self.now = NOW

    def _clock(self) -> datetime:
        return self.now

    def create(
        self, name: str, rules: tuple[dict[str, str], ...] = INCLUDE_ORDERS, *, description: str = ""
    ) -> CreateTableDiscoveryPolicyUseCaseOutput:
        """Create a policy."""
        return CreateTableDiscoveryPolicyService(self.policies, clock=self._clock).execute(
            CreateTableDiscoveryPolicyUseCaseInput(name=name, description=description, rules=rules)
        )

    def update(
        self, name: str, *, version: int, rules: tuple[dict[str, str], ...], description: str = ""
    ) -> UpdateTableDiscoveryPolicyUseCaseOutput:
        """Revise a policy from ``version``."""
        return UpdateTableDiscoveryPolicyService(
            self.policies,
            self.placements,
            self.requests,
            clock=self._clock,
            new_change_id=lambda: next(self.change_ids),
        ).execute(
            UpdateTableDiscoveryPolicyUseCaseInput(name=name, description=description, rules=rules, version=version)
        )

    def get(self, name: str) -> GetTableDiscoveryPolicyUseCaseOutput:
        """Get a policy at its current version."""
        return GetTableDiscoveryPolicyService(self.policies).execute(GetTableDiscoveryPolicyUseCaseInput(name=name))

    def get_version(self, name: str, version: int) -> GetTableDiscoveryPolicyVersionUseCaseOutput:
        """Get one stored version of a policy."""
        return GetTableDiscoveryPolicyVersionService(self.policies).execute(
            GetTableDiscoveryPolicyVersionUseCaseInput(name=name, version=version)
        )

    def delete(self, name: str) -> None:
        """Delete a policy."""
        DeleteTableDiscoveryPolicyService(self.policies, self.placements).execute(
            DeleteTableDiscoveryPolicyUseCaseInput(name=name)
        )

    def list(self) -> ListTableDiscoveryPoliciesUseCaseOutput:
        """List the policies."""
        return ListTableDiscoveryPoliciesService(self.policies, self.placements).execute(
            ListTableDiscoveryPoliciesUseCaseInput()
        )

    def policy_id(self, name: str) -> TableDiscoveryPolicyId:
        """Return the id of the stored policy ``name``."""
        policy = self.policies.get_by_name(TableDiscoveryPolicyName(value=name))
        assert policy is not None
        return policy.id

    def attach(self, name: str, catalog: str) -> None:
        """Put a policy on a catalog straight through its repo."""
        place = Catalog.register(CatalogId(catalog), NOW)
        place.attach_discovery_policy(self.policy_id(name), NOW)
        self.catalogs.create(place)

    def attach_namespace(self, name: str, catalog: str, *levels: str) -> None:
        """Put a policy on a namespace straight through its repo."""
        place = Namespace.register(NamespaceId.of(catalog, levels), NOW)
        place.attach_discovery_policy(self.policy_id(name), NOW)
        self.namespaces.create(place)

    def attach_table(self, name: str, table: TableName, uuid: str) -> None:
        """Put a policy on a table straight through its repo."""
        place = Table.register_undecided(TableId(uuid), table, NOW)
        place.attach_discovery_policy(self.policy_id(name), NOW)
        self.tables.create(place)

    def detach(self, name: str, catalog: str) -> None:
        """Take a policy off a catalog straight through its repo."""
        place = self.catalogs.get(CatalogId(catalog))
        assert place is not None
        place.detach_discovery_policy(self.policy_id(name), NOW)
        self.catalogs.update(place)


@pytest.fixture
def world() -> ServiceWorld:
    """Provide the services over empty fakes."""
    return ServiceWorld()


def test_create_builds_the_rules_in_order_and_starts_at_version_1(world: ServiceWorld) -> None:
    """The rules sent are the policy's rules, in the order sent; the policy starts at version 1."""
    created = world.create("mine", INCLUDE_ALL_BUT_TMP, description="no temporary tables")

    assert created.version == 1
    assert DP_ID.fullmatch(created.id)
    assert (created.created_at, created.updated_at) == (NOW, NOW)
    assert (created.description, created.rules) == ("no temporary tables", INCLUDE_ALL_BUT_TMP)
    assert world.get("mine").rules == INCLUDE_ALL_BUT_TMP


def test_create_accepts_exclude_rules_only(world: ServiceWorld) -> None:
    """A policy may hold exclude rules only."""
    created = world.create("mine", (_rule("exclude", "*"),))

    assert created.rules == ({"action": "exclude", "table_name_pattern": "*"},)


def test_create_with_a_taken_name_conflicts(world: ServiceWorld) -> None:
    """A second policy may not take a name."""
    world.create("mine")
    with pytest.raises(ConflictError, match="'mine' already exists"):
        world.create("mine")


@pytest.mark.parametrize(
    ("rules", "message"),
    [
        ((), "at least one rule"),
        ((_rule("manage", "*"),), "manage"),
        ((_rule("include", ""),), "must not be empty"),
        (({"action": "include"},), "table_name_pattern"),
        (({"table_name_pattern": "*"},), "action"),
        (({"action": "include", "table_name_pattern": "*", "outcome": "manage"},), "outcome"),
    ],
)
def test_create_refuses_bad_rules(world: ServiceWorld, rules: tuple[dict[str, str], ...], message: str) -> None:
    """No rule, an unknown action, an empty pattern, a missing or an unknown field is a validation error."""
    with pytest.raises(ValidationError, match=message):
        world.create("mine", rules)
    assert world.list().items == ()


def test_create_refuses_a_bad_name(world: ServiceWorld) -> None:
    """A name shaped like an id is a validation error."""
    with pytest.raises(ValidationError):
        world.create("dp-00000000000000000000000001")


def test_update_replaces_the_rules_and_bumps_the_version(world: ServiceWorld) -> None:
    """A revision holds the rules and description sent; the version increments."""
    world.create("mine")
    world.now = LATER

    updated = world.update("mine", version=1, rules=INCLUDE_ALL_BUT_TMP, description="second")

    assert updated.version == 2
    assert (updated.created_at, updated.updated_at) == (NOW, LATER)
    assert (updated.description, updated.rules) == ("second", INCLUDE_ALL_BUT_TMP)
    assert world.get("mine").rules == INCLUDE_ALL_BUT_TMP


def test_update_with_bad_rules_is_refused(world: ServiceWorld) -> None:
    """A revision with no rule is a validation error, and nothing is saved."""
    world.create("mine")
    with pytest.raises(ValidationError, match="at least one rule"):
        world.update("mine", version=1, rules=())
    assert world.get("mine").version == 1


def test_update_from_a_stale_version_conflicts(world: ServiceWorld) -> None:
    """An update from a version below or above the current one is a conflict, and nothing is saved."""
    world.create("mine")
    world.update("mine", version=1, rules=INCLUDE_ORDERS)

    with pytest.raises(ConflictError, match="is at version 2, not 1"):
        world.update("mine", version=1, rules=INCLUDE_ALL_BUT_TMP)
    with pytest.raises(ConflictError, match="is at version 2, not 3"):
        world.update("mine", version=3, rules=INCLUDE_ALL_BUT_TMP)
    current = world.get("mine")
    assert (current.version, current.rules) == (2, INCLUDE_ORDERS)


def test_update_rescans_the_catalogs_it_is_attached_in(world: ServiceWorld) -> None:
    """Once saved, each catalog the policy is attached in is scanned whole, once, under one change id."""
    world.create("mine")
    world.attach("mine", "prod")
    world.attach_namespace("mine", "dev", "sales")
    world.attach_table("mine", TableName(catalog="dev", namespace="sales.eu", table="orders"), "u-1")

    world.update("mine", version=1, rules=INCLUDE_ALL_BUT_TMP)

    assert [(r.catalog, r.namespace, r.change_id) for r in world.requests.calls] == [
        ("dev", None, "c1"),
        ("prod", None, "c1"),
    ]


def test_an_update_whose_scan_request_fails_still_stands(world: ServiceWorld) -> None:
    """A scan request that cannot be sent is logged; the revision is saved all the same."""
    world.create("mine")
    world.attach("mine", "prod")
    world.requests.failing.add("prod")

    world.update("mine", version=1, rules=INCLUDE_ALL_BUT_TMP)

    assert world.get("mine").version == 2


def test_an_update_of_a_policy_attached_nowhere_requests_no_scan(world: ServiceWorld) -> None:
    """A policy no place holds changes no table, so nothing is scanned."""
    world.create("mine")

    world.update("mine", version=1, rules=INCLUDE_ALL_BUT_TMP)

    assert world.requests.calls == []


def test_update_of_an_unknown_policy_is_not_found(world: ServiceWorld) -> None:
    """An update of a name no policy has is not found."""
    with pytest.raises(NotFoundError, match="discovery policy missing not found"):
        world.update("missing", version=1, rules=INCLUDE_ORDERS)


def test_deleting_a_policy_still_attached_is_refused_with_the_places(world: ServiceWorld) -> None:
    """A policy is not deleted while a place holds it; the refusal names each place, by type and then path."""
    world.create("mine")
    world.attach_table("mine", TableName(catalog="prod", namespace="sales.eu", table="orders"), "u-1")
    world.attach_namespace("mine", "prod", "sales")
    world.attach("mine", "prod")

    with pytest.raises(ConflictError) as refused:
        world.delete("mine")

    assert str(refused.value) == (
        "discovery policy mine is still attached to catalog:prod, namespace:prod.sales, table:prod.sales.eu.orders"
    )
    assert world.get("mine").version == 1


def test_delete_of_an_attached_policy_conflicts(world: ServiceWorld) -> None:
    """A policy is not deleted while it is attached; detached, it is."""
    world.create("mine")
    world.attach("mine", "prod")

    with pytest.raises(ConflictError, match="policy mine is still attached to catalog:prod"):
        world.delete("mine")
    assert world.get("mine").version == 1

    world.detach("mine", "prod")
    world.delete("mine")
    with pytest.raises(NotFoundError):
        world.get("mine")
    with pytest.raises(NotFoundError):
        world.get_version("mine", 1)


def test_delete_of_an_unknown_policy_is_not_found(world: ServiceWorld) -> None:
    """A delete of a name no policy has is not found."""
    with pytest.raises(NotFoundError, match="discovery policy missing not found"):
        world.delete("missing")


def test_a_version_stays_readable_after_an_update(world: ServiceWorld) -> None:
    """Each version keeps the description, rules and time it was written with; one never written is not found."""
    created = world.create("mine", INCLUDE_ORDERS, description="first")
    world.now = LATER
    world.update("mine", version=1, rules=INCLUDE_ALL_BUT_TMP, description="second")

    first = world.get_version("mine", 1)
    assert (first.id, first.name, first.version) == (created.id, "mine", 1)
    assert (first.description, first.rules, first.created_at) == ("first", INCLUDE_ORDERS, NOW)
    second = world.get_version("mine", 2)
    assert (second.description, second.rules, second.created_at) == ("second", INCLUDE_ALL_BUT_TMP, LATER)
    for version in (0, 3):
        with pytest.raises(NotFoundError, match=f"has no version {version}"):
            world.get_version("mine", version)


def test_get_refuses_an_unknown_name(world: ServiceWorld) -> None:
    """A name no policy has is not found."""
    with pytest.raises(NotFoundError, match="discovery policy missing not found"):
        world.get("missing")


def test_list_counts_attachments_by_name(world: ServiceWorld) -> None:
    """The policies come by name, each with how many targets it is attached to."""
    world.create("zeta", INCLUDE_ALL_BUT_TMP)
    world.create("alpha")
    world.attach("zeta", "prod")
    world.attach("zeta", "dev")

    listed = world.list().items

    assert [(p.name, p.attachment_count) for p in listed] == [("alpha", 0), ("zeta", 2)]
    assert listed[1].rules == world.get("zeta").rules
