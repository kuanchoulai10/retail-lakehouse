"""Test the SQL repository of the TableMaintenancePolicy aggregate."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool

from context.table_maintenance.adapter.outbound.shared.sql import create_schema
from context.table_maintenance.adapter.outbound.table_maintenance_policy.sql import (
    TableMaintenancePoliciesSqlRepo,
)
from context.table_maintenance.adapter.outbound.table_maintenance_policy_attachment.sql import (
    TableMaintenancePolicyAttachmentsSqlRepo,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    MaintenancePolicyContent,
    StalePolicyVersion,
    TableMaintenancePolicy,
    TableMaintenancePolicyName,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy_attachment import (
    PolicyTarget,
    PolicyTargetType,
    TableMaintenancePolicyAttachment,
)
from context.table_maintenance.application.exceptions import ConflictError

if TYPE_CHECKING:
    from sqlalchemy import Engine

NOW = datetime(2026, 10, 24, tzinfo=UTC)
NAME = TableMaintenancePolicyName("gold")


@pytest.fixture
def repo(engine: Engine) -> TableMaintenancePoliciesSqlRepo:
    """Provide the policies repository on the test engine."""
    return TableMaintenancePoliciesSqlRepo(engine)


def _policy() -> TableMaintenancePolicy:
    return TableMaintenancePolicy.create(NAME, MaintenancePolicyContent.platform_default(), NOW)


def test_roundtrip_of_a_policy_and_two_versions(repo: TableMaintenancePoliciesSqlRepo):
    """A policy with two versions loads back, both versions readable."""
    policy = _policy()
    repo.create(policy)
    first = MaintenancePolicyContent.platform_default()
    second = first.model_copy(update={"dry_run": True})
    policy.replace(second, expected_version=1, now=NOW + timedelta(hours=1))
    repo.update(policy)

    loaded = repo.get(NAME)
    assert loaded is not None
    assert loaded.version == 2
    assert loaded.content == second
    assert loaded.created_at == NOW
    assert loaded.created_at.tzinfo is not None
    assert loaded.updated_at == NOW + timedelta(hours=1)
    v1 = repo.get_version(NAME, 1)
    v2 = repo.get_version(NAME, 2)
    assert v1 is not None
    assert v1.content == first
    assert v1.created_at == NOW
    assert v2 is not None
    assert v2.content == second
    assert repo.get_version(NAME, 3) is None


def test_get_missing_returns_none(repo: TableMaintenancePoliciesSqlRepo):
    """Getting an unknown policy returns None."""
    assert repo.get(TableMaintenancePolicyName("nope")) is None


def test_duplicate_name_conflicts(repo: TableMaintenancePoliciesSqlRepo):
    """Creating a taken name raises ConflictError."""
    repo.create(_policy())
    with pytest.raises(ConflictError):
        repo.create(_policy())


def test_update_of_stale_aggregate_raises(repo: TableMaintenancePoliciesSqlRepo):
    """Persisting a version that skips ahead of the stored one is rejected."""
    repo.create(_policy())
    other = repo.get(NAME)
    assert other is not None
    mine = repo.get(NAME)
    assert mine is not None
    other.replace(MaintenancePolicyContent.platform_default(), expected_version=1, now=NOW)
    repo.update(other)
    mine.replace(MaintenancePolicyContent.platform_default(), expected_version=1, now=NOW)
    with pytest.raises(StalePolicyVersion):
        repo.update(mine)


def test_list_all_orders_by_name(repo: TableMaintenancePoliciesSqlRepo):
    """Policies are listed ordered by name."""
    repo.create(
        TableMaintenancePolicy.create(TableMaintenancePolicyName("b"), MaintenancePolicyContent.platform_default(), NOW)
    )
    repo.create(
        TableMaintenancePolicy.create(TableMaintenancePolicyName("a"), MaintenancePolicyContent.platform_default(), NOW)
    )
    assert [p.id.value for p in repo.list_all()] == ["a", "b"]


def test_delete_removes_versions_too(repo: TableMaintenancePoliciesSqlRepo):
    """Deleting a policy deletes its versions."""
    policy = _policy()
    repo.create(policy)
    policy.replace(MaintenancePolicyContent.platform_default(), expected_version=1, now=NOW)
    repo.update(policy)
    repo.delete(NAME)
    assert repo.get(NAME) is None
    assert repo.get_version(NAME, 1) is None
    assert repo.get_version(NAME, 2) is None


def _engine_enforcing_foreign_keys() -> Engine:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    event.listen(engine, "connect", lambda dbapi_connection, _: dbapi_connection.execute("PRAGMA foreign_keys=ON"))
    create_schema(engine)
    return engine


def test_delete_of_a_policy_attached_meanwhile_conflicts():
    """An attachment landing after the delete's check makes the delete a ConflictError and keeps the policy."""
    engine = _engine_enforcing_foreign_keys()
    repo = TableMaintenancePoliciesSqlRepo(engine)
    repo.create(_policy())
    target = PolicyTarget(type=PolicyTargetType.CATALOG, path=("prod",))
    TableMaintenancePolicyAttachmentsSqlRepo(engine).create(TableMaintenancePolicyAttachment.attach(target, NAME, NOW))
    with pytest.raises(ConflictError):
        repo.delete(NAME)
    assert repo.get(NAME) is not None
    assert repo.get_version(NAME, 1) is not None
