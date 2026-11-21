"""Test the repositories of the TableMaintenancePolicyAttachment aggregate."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import create_engine, event

from context.table_maintenance.adapter.outbound.shared.sql import create_schema
from context.table_maintenance.adapter.outbound.table_maintenance_policy.sql import (
    TableMaintenancePoliciesSqlRepo,
)
from context.table_maintenance.adapter.outbound.table_maintenance_policy_attachment.sql import (
    TableMaintenancePolicyAttachmentsSqlRepo,
)
from context.table_maintenance.application.domain.model.shared import PolicyTarget, PolicyTargetType
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    MaintenancePolicyContent,
    TableMaintenancePolicy,
    TableMaintenancePolicyId,
    TableMaintenancePolicyName,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy_attachment import (
    TableMaintenancePolicyAttachment,
)
from context.table_maintenance.application.exceptions import ConflictError
from tests.context.table_maintenance.fakes.in_memory_table_maintenance_policy_attachments_repo import (
    InMemoryTableMaintenancePolicyAttachmentsRepo,
)
from tests.context.table_maintenance.numbered_id import numbered_id

if TYPE_CHECKING:
    from pathlib import Path

    from sqlalchemy import Engine

    from context.table_maintenance.application.port.outbound.table_maintenance_policy_attachment import (
        TableMaintenancePolicyAttachmentsRepo,
    )

NOW = datetime(2026, 10, 24, tzinfo=UTC)
CATALOG = PolicyTarget(type=PolicyTargetType.CATALOG, path=("prod",))
NAMESPACE = PolicyTarget(type=PolicyTargetType.NAMESPACE, path=("prod", "sales", "eu"))
TABLE = PolicyTarget(type=PolicyTargetType.TABLE, path=("prod", "sales", "orders"), table_uuid="u-1")
POLICY_IDS = {
    "gold": TableMaintenancePolicyId(numbered_id("mp", 1)),
    "silver": TableMaintenancePolicyId(numbered_id("mp", 2)),
}


def _store_policies(engine: Engine) -> None:
    policies = TableMaintenancePoliciesSqlRepo(engine)
    for name, policy_id in POLICY_IDS.items():
        policies.create(
            TableMaintenancePolicy(
                id=policy_id,
                name=TableMaintenancePolicyName(value=name),
                content=MaintenancePolicyContent.platform_default(),
                version=1,
                created_at=NOW,
                updated_at=NOW,
            )
        )


@pytest.fixture(params=["sql", "memory"])
def repo(request: pytest.FixtureRequest, engine: Engine) -> TableMaintenancePolicyAttachmentsRepo:
    """Provide each repository implementation; the SQL one with the policies gold and silver stored."""
    if request.param == "sql":
        _store_policies(engine)
        return TableMaintenancePolicyAttachmentsSqlRepo(engine)
    return InMemoryTableMaintenancePolicyAttachmentsRepo()


def _attach(target: PolicyTarget, policy: str = "gold") -> TableMaintenancePolicyAttachment:
    return TableMaintenancePolicyAttachment.attach(target, POLICY_IDS[policy], NOW)


def test_roundtrip_of_each_target_type(repo: TableMaintenancePolicyAttachmentsRepo):
    """Catalog, namespace and table attachments load back equal in every field, by id and by target."""
    for target in (CATALOG, NAMESPACE, TABLE):
        attachment = _attach(target)
        repo.create(attachment)
        loaded = repo.get(attachment.id)
        assert loaded is not None
        assert loaded.id == attachment.id
        assert loaded.target == target
        assert loaded.policy_id == POLICY_IDS["gold"]
        assert loaded.attached_at == NOW
        assert repo.get_by_target(target) == loaded


def test_update_replaces_the_policy(repo: TableMaintenancePolicyAttachmentsRepo):
    """Updating an attachment stores its new policy."""
    attachment = _attach(CATALOG)
    repo.create(attachment)
    attachment.replace_policy(POLICY_IDS["silver"], NOW)
    repo.update(attachment)
    loaded = repo.get_by_target(CATALOG)
    assert loaded is not None
    assert loaded.id == attachment.id
    assert loaded.policy_id == POLICY_IDS["silver"]


def test_get_many_and_list_for_policy_and_delete(repo: TableMaintenancePolicyAttachmentsRepo):
    """Lookups by ids and by policy see the stored attachments; delete removes one."""
    catalog, namespace = _attach(CATALOG, "gold"), _attach(NAMESPACE, "silver")
    repo.create(catalog)
    repo.create(namespace)
    found = repo.get_many([namespace.id, _attach(TABLE).id])
    assert [a.id for a in found] == [namespace.id]
    assert [a.id for a in repo.list_for_policy(POLICY_IDS["gold"])] == [catalog.id]
    assert repo.has_attachments_for_policy(POLICY_IDS["silver"])
    repo.delete(namespace.id)
    assert not repo.has_attachments_for_policy(POLICY_IDS["silver"])
    assert len(repo.list_all()) == 1


def test_get_by_target_of_a_target_with_nothing_attached_is_none(repo: TableMaintenancePolicyAttachmentsRepo):
    """A target nothing is attached to finds no attachment."""
    repo.create(_attach(CATALOG))
    assert repo.get_by_target(NAMESPACE) is None


def test_get_by_target_finds_a_renamed_table_by_its_uuid(repo: TableMaintenancePolicyAttachmentsRepo):
    """A table target is found by uuid, whatever path it is asked under."""
    attachment = _attach(TABLE)
    repo.create(attachment)
    renamed = PolicyTarget(type=PolicyTargetType.TABLE, path=("prod", "archive", "orders_old"), table_uuid="u-1")
    loaded = repo.get_by_target(renamed)
    assert loaded is not None
    assert loaded.id == attachment.id


def test_get_many_by_targets_returns_the_attached_ones(repo: TableMaintenancePolicyAttachmentsRepo):
    """Only the targets that have an attachment are returned."""
    catalog, table = _attach(CATALOG), _attach(TABLE, "silver")
    repo.create(catalog)
    repo.create(table)
    found = repo.get_many_by_targets([TABLE, NAMESPACE, CATALOG])
    assert sorted(a.id.value for a in found) == sorted([catalog.id.value, table.id.value])
    assert repo.get_many_by_targets([]) == []


def test_second_attachment_on_one_target_conflicts(repo: TableMaintenancePolicyAttachmentsRepo):
    """A new attachment on a target that already has one is refused, and the first stays."""
    first, second = _attach(NAMESPACE, "gold"), _attach(NAMESPACE, "silver")
    assert first.id != second.id
    repo.create(first)
    with pytest.raises(ConflictError):
        repo.create(second)
    assert [a.id for a in repo.list_all()] == [first.id]


@pytest.fixture
def file_engine(tmp_path: Path) -> Engine:
    """Provide a SQLite database in a file, so two repositories share it like two API workers."""
    engine = create_engine(f"sqlite:///{tmp_path / 'db.sqlite'}")
    create_schema(engine)
    _store_policies(engine)
    return engine


def test_concurrent_attach_to_one_target_keeps_one(file_engine: Engine):
    """Two writers each create an attachment on one target: the unique target key refuses the second."""
    winner, loser = (
        TableMaintenancePolicyAttachmentsSqlRepo(file_engine),
        TableMaintenancePolicyAttachmentsSqlRepo(file_engine),
    )
    winner_attachment, loser_attachment = _attach(TABLE, "gold"), _attach(TABLE, "silver")
    assert winner_attachment.id != loser_attachment.id
    winner.create(winner_attachment)

    with pytest.raises(ConflictError):
        loser.create(loser_attachment)

    stored = loser.list_all()
    assert [(a.id, a.policy_id) for a in stored] == [(winner_attachment.id, POLICY_IDS["gold"])]


def test_attachment_to_an_unknown_policy_id_is_refused(tmp_path: Path):
    """The attachment's policy id is a foreign key to the stored policies."""
    engine = create_engine(f"sqlite:///{tmp_path / 'fk.sqlite'}")
    event.listen(engine, "connect", lambda dbapi_connection, _: dbapi_connection.execute("PRAGMA foreign_keys=ON"))
    create_schema(engine)
    _store_policies(engine)
    repo = TableMaintenancePolicyAttachmentsSqlRepo(engine)

    with pytest.raises(ConflictError):
        repo.create(TableMaintenancePolicyAttachment.attach(CATALOG, TableMaintenancePolicyId.new(), NOW))
    repo.create(_attach(CATALOG, "gold"))
    assert [a.policy_id for a in repo.list_all()] == [POLICY_IDS["gold"]]
