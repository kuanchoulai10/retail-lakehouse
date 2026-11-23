"""Test GetEffectivePoliciesService: which policy of each kind applies, from which level, through which attachment."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from context.table_maintenance.application.domain.model.shared import (
    TableDiscoveryPolicyAttachmentId,
    TableId,
    TableMaintenancePolicyAttachmentId,
)
from context.table_maintenance.application.domain.model.table import Table, TableName
from context.table_maintenance.application.domain.model.table_discovery_policy import DEFAULT_DISCOVERY_POLICY_ID
from context.table_maintenance.application.domain.model.table_maintenance_policy import MaintenancePolicyContent
from context.table_maintenance.application.exceptions import NotFoundError, ValidationError
from context.table_maintenance.application.port.inbound.table import (
    GetEffectivePoliciesUseCaseInput,
    GetEffectivePoliciesUseCaseOutput,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy import (
    CreateTableDiscoveryPolicyUseCaseInput,
    EnsureDefaultTableDiscoveryPolicyUseCaseInput,
    UpdateTableDiscoveryPolicyUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy_attachment import (
    AttachTableDiscoveryPolicyUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_policy import (
    CreateTableMaintenancePolicyUseCaseInput,
    EnsureDefaultTableMaintenancePolicyUseCaseInput,
    UpdateTableMaintenancePolicyUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_policy_attachment import (
    AttachTableMaintenancePolicyUseCaseInput,
)
from context.table_maintenance.application.port.outbound.table import CatalogAccessDeniedError
from context.table_maintenance.application.service.table import GetEffectivePoliciesService
from context.table_maintenance.application.service.table_discovery_policy import (
    CreateTableDiscoveryPolicyService,
    EnsureDefaultTableDiscoveryPolicyService,
    UpdateTableDiscoveryPolicyService,
)
from context.table_maintenance.application.service.table_discovery_policy_attachment import (
    AttachTableDiscoveryPolicyService,
)
from context.table_maintenance.application.service.table_maintenance_policy import (
    CreateTableMaintenancePolicyService,
    EnsureDefaultTableMaintenancePolicyService,
    UpdateTableMaintenancePolicyService,
)
from context.table_maintenance.application.service.table_maintenance_policy_attachment import (
    AttachTableMaintenancePolicyService,
)
from tests.context.table_maintenance.discovery_decision_samples import MANAGED
from tests.context.table_maintenance.fakes.fake_read_table_metadata_gateway import FakeReadTableMetadataGateway
from tests.context.table_maintenance.fakes.in_memory_table_discovery_policies_repo import (
    InMemoryTableDiscoveryPoliciesRepo,
)
from tests.context.table_maintenance.fakes.in_memory_table_discovery_policy_attachments_repo import (
    InMemoryTableDiscoveryPolicyAttachmentsRepo,
)
from tests.context.table_maintenance.fakes.in_memory_table_maintenance_policies_repo import (
    InMemoryTableMaintenancePoliciesRepo,
)
from tests.context.table_maintenance.fakes.in_memory_table_maintenance_policy_attachments_repo import (
    InMemoryTableMaintenancePolicyAttachmentsRepo,
)
from tests.context.table_maintenance.fakes.in_memory_tables_repo import InMemoryTablesRepo
from tests.context.table_maintenance.fakes.recording_send_discovery_request_gateway import (
    RecordingSendDiscoveryRequestGateway,
)
from tests.context.table_maintenance.fakes.recording_send_table_change_gateway import (
    RecordingSendTableChangeGateway,
)
from tests.context.table_maintenance.fakes.recording_sync_discovery_schedules_gateway import (
    RecordingSyncDiscoverySchedulesGateway,
)
from tests.context.table_maintenance.id_shape import IdShape

NOW = datetime(2026, 11, 1, tzinfo=UTC)
PA_ID = IdShape(TableMaintenancePolicyAttachmentId)
DA_ID = IdShape(TableDiscoveryPolicyAttachmentId)
MAINTENANCE_CONTENT = MaintenancePolicyContent.platform_default().to_primitives()
DISCOVERY_CONTENT = {
    "description": "Sales tables",
    "no_match_outcome": "manage",
    "rules": [
        {"outcome": "manage", "conditions": [{"attribute": "table_name", "operator": "glob", "values": ["orders_*"]}]}
    ],
}
ORDERS = ("prod", "sales", "eu", "orders")


class _World:
    """Run both kinds' attach services and the effective-policies service on fakes.

    Catalog ``prod`` holds ``sales.eu.orders`` (uuid ``u-1``); table maintenance records it only when a test
    calls ``record_orders``. Maintenance policy ``gold`` and discovery policy ``sales-tables`` exist beside the
    two platform defaults.
    """

    def __init__(self) -> None:
        self.maintenance_policies = InMemoryTableMaintenancePoliciesRepo()
        self.maintenance_attachments = InMemoryTableMaintenancePolicyAttachmentsRepo()
        self.discovery_policies = InMemoryTableDiscoveryPoliciesRepo()
        self.discovery_attachments = InMemoryTableDiscoveryPolicyAttachmentsRepo()
        self.gateway = FakeReadTableMetadataGateway()
        self.tables = InMemoryTablesRepo()
        self.changes = RecordingSendTableChangeGateway()
        self.gateway.add_table("prod", "sales.eu", "orders", "u-1")
        EnsureDefaultTableMaintenancePolicyService(self.maintenance_policies, clock=lambda: NOW).execute(
            EnsureDefaultTableMaintenancePolicyUseCaseInput()
        )
        EnsureDefaultTableDiscoveryPolicyService(self.discovery_policies, clock=lambda: NOW).execute(
            EnsureDefaultTableDiscoveryPolicyUseCaseInput()
        )
        CreateTableMaintenancePolicyService(self.maintenance_policies, clock=lambda: NOW).execute(
            CreateTableMaintenancePolicyUseCaseInput(name="gold", content=MAINTENANCE_CONTENT)
        )
        CreateTableDiscoveryPolicyService(self.discovery_policies, clock=lambda: NOW).execute(
            CreateTableDiscoveryPolicyUseCaseInput(name="sales-tables", content=DISCOVERY_CONTENT)
        )
        self.service = GetEffectivePoliciesService(
            self.maintenance_policies,
            self.maintenance_attachments,
            self.discovery_policies,
            self.discovery_attachments,
            self.gateway,
            self.tables,
        )

    def record_orders(self, name: TableName | None = None) -> None:
        self.tables.create(
            Table.register(
                TableId("u-1"),
                name or TableName(catalog="prod", namespace="sales.eu", table="orders"),
                MANAGED,
                NOW,
            )
        )

    def attach_maintenance(self, policy: str, type_: str, path: tuple[str, ...]) -> None:
        AttachTableMaintenancePolicyService(
            self.maintenance_policies,
            self.maintenance_attachments,
            self.gateway,
            self.tables,
            self.changes,
            clock=lambda: NOW,
        ).execute(AttachTableMaintenancePolicyUseCaseInput(target_type=type_, path=path, policy_name=policy))

    def attach_discovery(self, policy: str, type_: str, path: tuple[str, ...]) -> None:
        AttachTableDiscoveryPolicyService(
            self.discovery_policies,
            self.discovery_attachments,
            self.gateway,
            RecordingSendDiscoveryRequestGateway(),
            RecordingSyncDiscoverySchedulesGateway(),
            clock=lambda: NOW,
        ).execute(AttachTableDiscoveryPolicyUseCaseInput(policy_name=policy, target_type=type_, path=path))

    def maintenance_attachment_id(self) -> str:
        (attachment,) = self.maintenance_attachments.list_all()
        return attachment.id.value

    def discovery_attachment_id(self) -> str:
        (attachment,) = self.discovery_attachments.list_all()
        return attachment.id.value

    def by_uuid(self, table_uuid: str) -> GetEffectivePoliciesUseCaseOutput:
        return self.service.execute(GetEffectivePoliciesUseCaseInput(table_uuid=table_uuid))

    def by_location(
        self, catalog: str, namespace: str | None = None, table: str | None = None
    ) -> GetEffectivePoliciesUseCaseOutput:
        return self.service.execute(GetEffectivePoliciesUseCaseInput(catalog=catalog, namespace=namespace, table=table))


@pytest.fixture
def world() -> _World:
    """Provide the services over fakes."""
    return _World()


def test_a_table_with_nothing_attached_gets_both_platform_defaults(world: _World) -> None:
    """With nothing attached each kind falls back to its platform default, read from its repo."""
    world.record_orders()

    out = world.by_uuid("u-1")

    maintenance, discovery = out.maintenance, out.discovery
    assert (maintenance.policy_id, maintenance.policy_name, maintenance.version) == (
        "mp-00000000000000000000000000",
        "default",
        1,
    )
    assert (maintenance.description, maintenance.dry_run) == ("Platform default", False)
    assert (maintenance.target, maintenance.attachment_id) == (None, None)
    assert (discovery.policy_id, discovery.policy_name, discovery.version) == (
        "dp-00000000000000000000000000",
        "default",
        1,
    )
    assert discovery.no_match_outcome == "unmanage"
    assert (discovery.target, discovery.attachment_id) == (None, None)


def test_the_default_discovery_policy_is_read_from_its_repo(world: _World) -> None:
    """The default discovery entry carries the stored policy, not one made up in memory."""
    world.discovery_policies.delete(DEFAULT_DISCOVERY_POLICY_ID)
    world.record_orders()

    with pytest.raises(NotFoundError):
        world.by_uuid("u-1")


def test_each_kind_takes_its_own_nearest_attachment(world: _World) -> None:
    """A table attachment wins for its kind only; the other kind still answers from its own level."""
    world.record_orders()
    world.attach_maintenance("gold", "table", ORDERS)
    world.attach_maintenance("default", "namespace", ("prod", "sales"))
    world.attach_discovery("sales-tables", "namespace", ("prod", "sales"))

    out = world.by_uuid("u-1")

    gold_attachment = next(a for a in world.maintenance_attachments.list_all() if a.target.type == "table")
    assert out.maintenance.policy_name == "gold"
    assert out.maintenance.policy_id == gold_attachment.policy_id.value
    assert out.maintenance.target == {"type": "table", "path": list(ORDERS), "table_uuid": "u-1"}
    assert out.maintenance.attachment_id == gold_attachment.id.value
    assert PA_ID.fullmatch(out.maintenance.attachment_id or "")
    assert out.discovery.policy_name == "sales-tables"
    assert (out.discovery.description, out.discovery.no_match_outcome) == ("Sales tables", "manage")
    assert out.discovery.target == {"type": "namespace", "path": ["prod", "sales"]}
    assert out.discovery.attachment_id == world.discovery_attachment_id()
    assert DA_ID.fullmatch(out.discovery.attachment_id or "")


def test_the_version_is_the_policys_latest(world: _World) -> None:
    """An attachment means the policy's latest version, so updating either kind's policy moves its answer."""
    world.record_orders()
    world.attach_maintenance("gold", "catalog", ("prod",))
    world.attach_discovery("sales-tables", "catalog", ("prod",))
    UpdateTableMaintenancePolicyService(
        world.maintenance_policies, world.maintenance_attachments, world.tables, world.changes, clock=lambda: NOW
    ).execute(
        UpdateTableMaintenancePolicyUseCaseInput(
            name="gold", content={**MAINTENANCE_CONTENT, "description": "Gold v2", "dry_run": True}, version=1
        )
    )

    UpdateTableDiscoveryPolicyService(
        world.discovery_policies,
        world.discovery_attachments,
        RecordingSendDiscoveryRequestGateway(),
        RecordingSyncDiscoverySchedulesGateway(),
        clock=lambda: NOW,
    ).execute(
        UpdateTableDiscoveryPolicyUseCaseInput(
            name="sales-tables",
            content={"description": "Sales v2", "no_match_outcome": "unmanage", "rules": []},
            version=1,
        )
    )

    out = world.by_uuid("u-1")

    assert (out.maintenance.version, out.maintenance.description, out.maintenance.dry_run) == (2, "Gold v2", True)
    assert (out.discovery.version, out.discovery.description, out.discovery.no_match_outcome) == (
        2,
        "Sales v2",
        "unmanage",
    )


def test_a_table_unknown_to_maintenance_is_answered_by_location(world: _World) -> None:
    """A table not recorded is placed by the catalog; a table attachment made by uuid is found."""
    world.attach_maintenance("gold", "table", ORDERS)
    world.attach_discovery("sales-tables", "table", ORDERS)
    assert world.tables.list_all() == []

    out = world.by_location("prod", "sales.eu", "orders")

    assert (out.maintenance.policy_name, out.maintenance.attachment_id) == ("gold", world.maintenance_attachment_id())
    assert (out.discovery.policy_name, out.discovery.attachment_id) == (
        "sales-tables",
        world.discovery_attachment_id(),
    )
    assert (
        out.maintenance.target == out.discovery.target == {"type": "table", "path": list(ORDERS), "table_uuid": "u-1"}
    )


def test_a_namespace_or_catalog_is_answered_by_location(world: _World) -> None:
    """A namespace starts at itself, a catalog at itself; table attachments below them do not count."""
    world.attach_maintenance("gold", "table", ORDERS)
    world.attach_maintenance("default", "namespace", ("prod", "sales"))
    world.attach_discovery("sales-tables", "catalog", ("prod",))

    namespace = world.by_location("prod", "sales.eu")
    catalog = world.by_location("prod")

    assert namespace.maintenance.target == {"type": "namespace", "path": ["prod", "sales"]}
    assert namespace.discovery.target == {"type": "catalog", "path": ["prod"]}
    assert (catalog.maintenance.target, catalog.maintenance.policy_name) == (None, "default")
    assert (catalog.discovery.target, catalog.discovery.policy_name) == (
        {"type": "catalog", "path": ["prod"]},
        "sales-tables",
    )


def test_by_uuid_the_table_is_placed_by_its_record_not_where_it_was_attached(world: _World) -> None:
    """After a rename the table attachment follows the uuid and names the table where it is now."""
    world.attach_maintenance("gold", "table", ORDERS)
    world.attach_discovery("sales-tables", "namespace", ("prod", "sales"))
    world.gateway.drop_table("prod", "sales.eu", "orders")
    world.gateway.add_table("prod", "archive", "orders_old", "u-1")
    world.record_orders(TableName(catalog="prod", namespace="archive", table="orders_old"))

    out = world.by_uuid("u-1")

    assert out.maintenance.policy_name == "gold"
    assert out.maintenance.target == {"type": "table", "path": ["prod", "archive", "orders_old"], "table_uuid": "u-1"}
    assert (out.discovery.policy_name, out.discovery.target) == ("default", None)


def test_a_table_by_location_reads_its_place_only_by_loading_the_table(world: _World) -> None:
    """Loading the table proves its catalog and namespace exist, so neither is asked about again."""
    world.by_location("prod", "sales.eu", "orders")

    assert [name for name, _ in world.gateway.calls] == ["load_table"]


def test_a_namespace_by_location_is_checked_with_one_read(world: _World) -> None:
    """A namespace read also tells whether its catalog exists."""
    world.by_location("prod", "sales.eu")

    assert world.gateway.calls == [("namespace_exists", ("prod", "sales.eu"))]


@pytest.mark.parametrize(
    "location", [{"catalog": "prod"}, {"catalog": "prod", "namespace": "sales.eu", "table": "orders"}]
)
def test_a_uuid_with_a_location_is_refused(world: _World, location: dict[str, str]) -> None:
    """A place is named by uuid or by location, never both."""
    world.record_orders()

    with pytest.raises(ValidationError, match="by uuid or by location"):
        world.service.execute(GetEffectivePoliciesUseCaseInput(table_uuid="u-1", **location))


def test_by_uuid_a_table_without_a_record_is_not_found(world: _World) -> None:
    """By uuid only a table maintenance records can be placed; the catalog has no read by uuid."""
    with pytest.raises(NotFoundError):
        world.by_uuid("u-1")


@pytest.mark.parametrize(
    ("catalog", "namespace", "table"),
    [
        ("prod", "sales.eu", "missing"),
        ("prod", "nowhere", None),
        ("prod", "nowhere", "orders"),
        ("gone", None, None),
        ("gone", "sales", None),
    ],
)
def test_by_location_a_missing_table_namespace_or_catalog_is_not_found(
    world: _World, catalog: str, namespace: str | None, table: str | None
) -> None:
    """A place the catalog does not hold is not found."""
    with pytest.raises(NotFoundError):
        world.by_location(catalog, namespace, table)


def test_by_location_a_dropped_catalog_is_not_found(world: _World) -> None:
    """A catalog the server no longer has reads as not found, not as a failure."""
    world.gateway.drop_catalog("prod")

    for namespace in (None, "sales"):
        with pytest.raises(NotFoundError):
            world.by_location("prod", namespace)


def test_an_empty_catalog_and_namespace_are_answered(world: _World) -> None:
    """A place may hold no table."""
    world.gateway.add_namespace("empty", "nothing.here")

    assert world.by_location("empty").maintenance.policy_name == "default"
    assert world.by_location("empty", "nothing.here").discovery.policy_name == "default"


@pytest.mark.parametrize(("namespace", "table"), [(None, None), ("sales.eu", None), ("sales.eu", "orders")])
def test_a_catalog_the_platform_cannot_read_is_refused(world: _World, namespace: str | None, table: str | None) -> None:
    """A catalog the platform's credential cannot read is refused, as attach refuses it."""
    world.gateway.deny("prod")

    with pytest.raises(CatalogAccessDeniedError):
        world.by_location("prod", namespace, table)


def test_neither_a_catalog_nor_a_uuid_is_refused(world: _World) -> None:
    """A request naming no place is refused."""
    with pytest.raises(ValidationError):
        world.service.execute(GetEffectivePoliciesUseCaseInput())
