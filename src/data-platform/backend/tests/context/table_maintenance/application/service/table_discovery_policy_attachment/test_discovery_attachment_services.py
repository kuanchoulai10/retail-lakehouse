"""Test the attach, detach and list services of discovery policy attachments."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from context.table_maintenance.application.domain.model.table_discovery_policy import TableDiscoveryPolicyName
from context.table_maintenance.application.domain.model.table_maintenance_policy_attachment import (
    TableMaintenancePolicyAttachmentId,
)
from context.table_maintenance.application.exceptions import NotFoundError, ValidationError
from context.table_maintenance.application.port.inbound.table_discovery_policy import (
    CreateTableDiscoveryPolicyUseCaseInput,
    EnsureDefaultTableDiscoveryPolicyUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy_attachment import (
    AttachTableDiscoveryPolicyUseCaseInput,
    AttachTableDiscoveryPolicyUseCaseOutput,
    DetachTableDiscoveryPolicyUseCaseInput,
    DetachTableDiscoveryPolicyUseCaseOutput,
    ListTableDiscoveryPolicyAttachmentsUseCaseInput,
    ListTableDiscoveryPolicyAttachmentsUseCaseOutput,
)
from context.table_maintenance.application.port.outbound.table import CatalogAccessDeniedError
from context.table_maintenance.application.service.table_discovery_policy import (
    CreateTableDiscoveryPolicyService,
    EnsureDefaultTableDiscoveryPolicyService,
)
from context.table_maintenance.application.service.table_discovery_policy_attachment import (
    AttachTableDiscoveryPolicyService,
    DetachTableDiscoveryPolicyService,
    ListTableDiscoveryPolicyAttachmentsService,
)
from shared_kernel import prefixed_id_pattern
from tests.context.table_maintenance.fakes.fake_read_table_metadata_gateway import FakeReadTableMetadataGateway
from tests.context.table_maintenance.fakes.in_memory_table_discovery_policies_repo import (
    InMemoryTableDiscoveryPoliciesRepo,
)
from tests.context.table_maintenance.fakes.in_memory_table_discovery_policy_attachments_repo import (
    InMemoryTableDiscoveryPolicyAttachmentsRepo,
)
from tests.context.table_maintenance.fakes.in_memory_tables_repo import InMemoryTablesRepo

NOW = datetime(2026, 11, 1, tzinfo=UTC)
LATER = datetime(2026, 11, 2, tzinfo=UTC)
DA_ID = prefixed_id_pattern("da")
CONTENT = {
    "description": "",
    "no_match_outcome": "unmanage",
    "rules": [
        {"outcome": "manage", "conditions": [{"attribute": "table_name", "operator": "glob", "values": ["orders_*"]}]}
    ],
}
ORDERS = ("iceberg", "sales", "eu", "orders")


class _World:
    """Run the attachment services on fakes: policies ``mine`` and ``other``, and catalog ``iceberg``.

    ``iceberg`` holds the table ``sales.eu.orders`` (uuid ``u-1``), which table maintenance does not know.
    """

    def __init__(self) -> None:
        self.attachments = InMemoryTableDiscoveryPolicyAttachmentsRepo()
        self.policies = InMemoryTableDiscoveryPoliciesRepo()
        self.catalog = FakeReadTableMetadataGateway()
        self.tables = InMemoryTablesRepo()
        self.now = NOW
        self.catalog.add_table("iceberg", "sales.eu", "orders", "u-1")
        EnsureDefaultTableDiscoveryPolicyService(self.policies, clock=lambda: NOW).execute(
            EnsureDefaultTableDiscoveryPolicyUseCaseInput()
        )
        for name in ("mine", "other"):
            CreateTableDiscoveryPolicyService(self.policies, clock=lambda: NOW).execute(
                CreateTableDiscoveryPolicyUseCaseInput(name=name, content=CONTENT)
            )

    def attach(self, policy: str, type_: str, path: tuple[str, ...]) -> AttachTableDiscoveryPolicyUseCaseOutput:
        return AttachTableDiscoveryPolicyService(
            self.policies, self.attachments, self.catalog, clock=lambda: self.now
        ).execute(AttachTableDiscoveryPolicyUseCaseInput(policy_name=policy, target_type=type_, path=path))

    def detach(self, policy: str, attachment_id: str) -> DetachTableDiscoveryPolicyUseCaseOutput:
        return DetachTableDiscoveryPolicyService(self.policies, self.attachments).execute(
            DetachTableDiscoveryPolicyUseCaseInput(policy_name=policy, attachment_id=attachment_id)
        )

    def list(self, policy: str) -> ListTableDiscoveryPolicyAttachmentsUseCaseOutput:
        return ListTableDiscoveryPolicyAttachmentsService(
            self.policies, self.attachments, self.catalog, self.tables
        ).execute(ListTableDiscoveryPolicyAttachmentsUseCaseInput(policy_name=policy))

    def policy_id(self, name: str) -> str:
        policy = self.policies.get_by_name(TableDiscoveryPolicyName(value=name))
        assert policy is not None
        return policy.id.value


@pytest.fixture
def world() -> _World:
    """Provide the attachment services over fakes."""
    return _World()


def test_attach_to_a_table_resolves_its_uuid_from_the_catalog(world: _World) -> None:
    """A table target is keyed by the uuid the catalog gives; the table need not be managed."""
    out = world.attach("mine", "table", ORDERS)

    assert DA_ID.fullmatch(out.id)
    assert (out.target_type, out.path, out.table_uuid) == ("table", ORDERS, "u-1")
    assert (out.policy_id, out.policy_name, out.attached_at) == (world.policy_id("mine"), "mine", NOW)
    assert world.tables.list_all() == []
    (stored,) = world.attachments.list_all()
    assert (stored.id.value, stored.target.table_uuid) == (out.id, "u-1")


def test_attach_replaces_the_targets_policy_and_keeps_the_id(world: _World) -> None:
    """Attaching to a target that holds another policy replaces it under the same ``da-`` id."""
    first = world.attach("mine", "catalog", ("iceberg",))
    world.now = LATER

    second = world.attach("other", "catalog", ("iceberg",))

    assert second.id == first.id
    assert (second.policy_id, second.policy_name, second.attached_at) == (world.policy_id("other"), "other", LATER)
    (stored,) = world.attachments.list_all()
    assert (stored.id.value, stored.policy_id.value, stored.attached_at) == (first.id, world.policy_id("other"), LATER)
    assert world.list("mine").items == ()


def test_attach_to_an_empty_catalog(world: _World) -> None:
    """A catalog that holds nothing yet may be attached to."""
    world.catalog.add_catalog("fresh")

    out = world.attach("mine", "catalog", ("fresh",))

    (stored,) = world.attachments.list_all()
    assert (stored.id.value, stored.target.path, stored.catalog) == (out.id, ("fresh",), "fresh")


def test_attach_to_an_empty_namespace(world: _World) -> None:
    """A namespace that holds no table may be attached to."""
    world.catalog.add_namespace("iceberg", "staging")

    world.attach("mine", "namespace", ("iceberg", "staging"))

    assert [a.target.path for a in world.attachments.list_all()] == [("iceberg", "staging")]


def test_attach_to_a_missing_namespace_is_not_found(world: _World) -> None:
    """A namespace the catalog does not hold is NotFoundError, and nothing is stored."""
    with pytest.raises(NotFoundError, match=r"namespace iceberg\.ghost not found"):
        world.attach("mine", "namespace", ("iceberg", "ghost"))

    assert world.attachments.list_all() == []


@pytest.mark.parametrize(
    ("type_", "path"),
    [("catalog", ("nope",)), ("table", ("iceberg", "sales", "eu", "ghost"))],
)
def test_attach_to_a_missing_catalog_or_table_is_not_found(world: _World, type_: str, path: tuple[str, ...]) -> None:
    """A catalog or table the catalog does not hold is NotFoundError, and nothing is stored."""
    with pytest.raises(NotFoundError, match="not found"):
        world.attach("mine", type_, path)

    assert world.attachments.list_all() == []


@pytest.mark.parametrize(
    ("type_", "path"),
    [("catalog", ("iceberg",)), ("namespace", ("iceberg", "sales")), ("table", ORDERS)],
)
def test_attach_in_a_refused_catalog_is_access_denied(world: _World, type_: str, path: tuple[str, ...]) -> None:
    """A target in a catalog the credential cannot read raises CatalogAccessDeniedError, and nothing is stored."""
    world.catalog.deny("iceberg")

    with pytest.raises(CatalogAccessDeniedError, match="cannot read catalog iceberg"):
        world.attach("mine", type_, path)

    assert world.attachments.list_all() == []


def test_attach_of_an_unknown_policy_is_not_found(world: _World) -> None:
    """Attaching a policy that does not exist is NotFoundError, and nothing is stored."""
    with pytest.raises(NotFoundError, match="discovery policy ghost not found"):
        world.attach("ghost", "catalog", ("iceberg",))

    assert world.attachments.list_all() == []


def test_attach_with_a_bad_target_type_is_a_validation_error(world: _World) -> None:
    """An unknown target type is ValidationError."""
    with pytest.raises(ValidationError):
        world.attach("mine", "warehouse", ("iceberg",))


def test_attach_the_default_opts_a_target_out(world: _World) -> None:
    """The default policy may be attached like any other."""
    out = world.attach("default", "namespace", ("iceberg", "sales"))

    assert (out.policy_id, out.policy_name) == ("dp-00000000000000000000000000", "default")


def test_detach_by_id(world: _World) -> None:
    """Detaching by attachment id removes it from the policy's list."""
    kept = world.attach("mine", "catalog", ("iceberg",))
    gone = world.attach("mine", "namespace", ("iceberg", "sales"))

    world.detach("mine", gone.id)

    assert [item.id for item in world.list("mine").items] == [kept.id]


def test_detach_of_another_policys_attachment_is_not_found(world: _World) -> None:
    """An attachment of another policy is not this policy's to detach; it stays."""
    a = world.attach("other", "catalog", ("iceberg",))

    with pytest.raises(NotFoundError, match=f"policy mine has no attachment {a.id}"):
        world.detach("mine", a.id)

    assert world.list("other").items[0].id == a.id


def test_detach_of_an_unknown_attachment_is_not_found(world: _World) -> None:
    """A well-formed ``da-`` id that is not stored is NotFoundError."""
    unknown = "da-00000000000000000000000000"

    with pytest.raises(NotFoundError, match=f"policy mine has no attachment {unknown}"):
        world.detach("mine", unknown)


@pytest.mark.parametrize("attachment_id", ["x", "", TableMaintenancePolicyAttachmentId.new().value])
def test_detach_with_a_malformed_id_is_a_validation_error(world: _World, attachment_id: str) -> None:
    """An id that is not a ``da-`` id, a maintenance ``pa-`` id among them, is ValidationError."""
    world.attach("mine", "catalog", ("iceberg",))

    with pytest.raises(ValidationError, match="da-"):
        world.detach("mine", attachment_id)

    assert len(world.attachments.list_all()) == 1


def test_detach_from_an_unknown_policy_is_not_found(world: _World) -> None:
    """Detaching from a policy that does not exist is NotFoundError."""
    a = world.attach("mine", "catalog", ("iceberg",))

    with pytest.raises(NotFoundError, match="discovery policy ghost not found"):
        world.detach("ghost", a.id)


def test_detach_works_for_an_orphaned_target(world: _World) -> None:
    """A target whose catalog is gone is detached by id without reading the catalog."""
    by_namespace = world.attach("mine", "namespace", ("iceberg", "sales"))
    by_table = world.attach("mine", "table", ORDERS)
    world.catalog.drop_catalog("iceberg")
    reads = len(world.catalog.calls)

    world.detach("mine", by_namespace.id)
    world.detach("mine", by_table.id)

    assert world.attachments.list_all() == []
    assert len(world.catalog.calls) == reads


def test_list_carries_each_attachment(world: _World) -> None:
    """Each listed attachment carries its id, target, policy and when it was attached."""
    a = world.attach("mine", "table", ORDERS)

    (item,) = world.list("mine").items

    assert (item.id, item.type, item.path, item.table_uuid) == (a.id, "table", ORDERS, "u-1")
    assert (item.policy_id, item.policy_name, item.attached_at, item.orphaned) == (
        world.policy_id("mine"),
        "mine",
        NOW,
        False,
    )


def test_list_marks_a_target_that_left_the_catalog_orphaned(world: _World) -> None:
    """A namespace or table no longer in the catalog is orphaned; a catalog that still exists is not."""
    world.attach("mine", "catalog", ("iceberg",))
    world.attach("mine", "namespace", ("iceberg", "sales", "eu"))
    world.attach("mine", "table", ORDERS)
    world.catalog.drop_namespace("iceberg", "sales.eu")

    listed = sorted((item.type, item.orphaned) for item in world.list("mine").items)

    assert listed == [("catalog", False), ("namespace", True), ("table", True)]


def test_list_marks_every_target_of_a_dropped_catalog_orphaned(world: _World) -> None:
    """A catalog that is gone orphans itself and everything attached in it."""
    world.attach("mine", "catalog", ("iceberg",))
    world.attach("mine", "namespace", ("iceberg", "sales"))
    world.catalog.drop_catalog("iceberg")

    assert {item.orphaned for item in world.list("mine").items} == {True}


def test_list_in_a_refused_catalog_is_not_orphaned(world: _World) -> None:
    """A catalog the credential cannot read is not known to be gone: its targets are listed, none orphaned."""
    world.attach("mine", "catalog", ("iceberg",))
    world.attach("mine", "namespace", ("iceberg", "sales"))
    world.attach("mine", "table", ORDERS)
    world.catalog.deny("iceberg")

    items = world.list("mine").items

    assert sorted((item.type, item.orphaned) for item in items) == [
        ("catalog", False),
        ("namespace", False),
        ("table", False),
    ]


def test_list_shows_only_the_policys_attachments(world: _World) -> None:
    """Another policy's attachments are not listed."""
    world.attach("other", "catalog", ("iceberg",))
    mine = world.attach("mine", "namespace", ("iceberg", "sales"))

    assert [item.id for item in world.list("mine").items] == [mine.id]


def test_list_of_an_unknown_policy_is_not_found(world: _World) -> None:
    """Listing the attachments of a policy that does not exist is NotFoundError."""
    with pytest.raises(NotFoundError, match="discovery policy ghost not found"):
        world.list("ghost")
