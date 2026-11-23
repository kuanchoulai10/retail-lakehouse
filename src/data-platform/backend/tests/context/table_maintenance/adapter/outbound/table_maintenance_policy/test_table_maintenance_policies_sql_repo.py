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
from context.table_maintenance.application.domain.model.shared import (
    PolicyTarget,
    PolicyTargetType,
    TableMaintenancePolicyId,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    MaintenancePolicyContent,
    StalePolicyVersion,
    TableMaintenancePolicy,
    TableMaintenancePolicyName,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy_attachment import (
    TableMaintenancePolicyAttachment,
)
from context.table_maintenance.application.exceptions import ConflictError

if TYPE_CHECKING:
    from sqlalchemy import Engine

NOW = datetime(2026, 10, 24, tzinfo=UTC)
NAME = TableMaintenancePolicyName(value="gold")


@pytest.fixture
def repo(engine: Engine) -> TableMaintenancePoliciesSqlRepo:
    """Provide the policies repository on the test engine."""
    return TableMaintenancePoliciesSqlRepo(engine)


def _policy(name: str = "gold") -> TableMaintenancePolicy:
    return TableMaintenancePolicy.create(
        TableMaintenancePolicyName(value=name), MaintenancePolicyContent.platform_default(), NOW
    )


def test_roundtrip_of_a_policy_and_two_versions(repo: TableMaintenancePoliciesSqlRepo):
    """A policy with two versions loads back by its id, both versions readable."""
    policy = _policy()
    repo.create(policy)
    first = MaintenancePolicyContent.platform_default()
    second = first.model_copy(update={"dry_run": True})
    policy.replace(second, expected_version=1, now=NOW + timedelta(hours=1))
    repo.update(policy)

    loaded = repo.get(policy.id)
    assert loaded is not None
    assert loaded.id == policy.id
    assert loaded.name == NAME
    assert loaded.version == 2
    assert loaded.content == second
    assert loaded.created_at == NOW
    assert loaded.created_at.tzinfo is not None
    assert loaded.updated_at == NOW + timedelta(hours=1)
    v1 = repo.get_version(policy.id, 1)
    v2 = repo.get_version(policy.id, 2)
    assert v1 is not None
    assert v1.policy_id == policy.id
    assert v1.content == first
    assert v1.created_at == NOW
    assert v2 is not None
    assert v2.content == second
    assert repo.get_version(policy.id, 3) is None


def test_sql_round_trip_keeps_every_block(repo: TableMaintenancePoliciesSqlRepo):
    """A content with every option set and one block left out reads back equal."""
    content = MaintenancePolicyContent.from_primitives(
        {
            "description": "everything",
            "on": {"schedule": {"every_seconds": 600}, "catalog_commit": {"debounce_seconds": 0}},
            "dry_run": True,
            "rewrite_data_files": {
                "target": {"reducible_files": {"at_most": 0}, "per": "table"},
                "options": {
                    "strategy": "sort",
                    "sort_order": "id DESC NULLS LAST",
                    "min_input_files": 3,
                    "partial_progress_enabled": True,
                    "partial_progress_max_commits": 4,
                    "max_concurrent_file_group_rewrites": 5,
                    "rewrite_all": False,
                    "delete_file_threshold": 6,
                    "remove_dangling_deletes": True,
                    "max_file_group_size_bytes": 1073741824,
                },
            },
            "rewrite_manifests": {"target": {"small_manifests": {"at_most": 2}}, "options": {"use_caching": False}},
            "expire_snapshots": {
                "target": {"max_snapshot_age_seconds": 7200},
                "options": {"max_concurrent_deletes": 8, "stream_results": True},
            },
        }
    )
    policy = TableMaintenancePolicy.create(NAME, content, NOW)
    repo.create(policy)
    loaded = repo.get(policy.id)
    assert loaded is not None
    assert loaded.content == content
    assert loaded.content.remove_orphan_files is None
    version = repo.get_version(policy.id, 1)
    assert version is not None
    assert version.content.to_primitives() == content.to_primitives()


def test_get_missing_returns_none(repo: TableMaintenancePoliciesSqlRepo):
    """Getting an unknown policy returns None."""
    assert repo.get(TableMaintenancePolicyId.new()) is None


def test_get_by_name_finds_the_policy(repo: TableMaintenancePoliciesSqlRepo):
    """A policy is found by its name, which is what a URL names it by; an unknown name is None."""
    policy = _policy()
    repo.create(policy)

    found = repo.get_by_name(NAME)

    assert found is not None
    assert found.id == policy.id
    assert repo.get_by_name(TableMaintenancePolicyName(value="nope")) is None


def test_get_many_returns_the_existing_ones(repo: TableMaintenancePoliciesSqlRepo):
    """``get_many`` returns the policies that exist among the ids, skipping unknown ones."""
    gold, silver = _policy("gold"), _policy("silver")
    repo.create(gold)
    repo.create(silver)

    found = repo.get_many([gold.id, TableMaintenancePolicyId.new(), silver.id])

    assert sorted(p.name.value for p in found) == ["gold", "silver"]
    assert repo.get_many([]) == []


def test_duplicate_name_conflicts(repo: TableMaintenancePoliciesSqlRepo):
    """A second policy with a taken name raises ConflictError, though its id is new."""
    repo.create(_policy())
    other = _policy()
    with pytest.raises(ConflictError):
        repo.create(other)
    assert repo.get(other.id) is None


def test_update_of_stale_aggregate_raises(repo: TableMaintenancePoliciesSqlRepo):
    """Persisting a version that skips ahead of the stored one is rejected."""
    policy = _policy()
    repo.create(policy)
    other = repo.get(policy.id)
    assert other is not None
    mine = repo.get(policy.id)
    assert mine is not None
    other.replace(MaintenancePolicyContent.platform_default(), expected_version=1, now=NOW)
    repo.update(other)
    mine.replace(MaintenancePolicyContent.platform_default(), expected_version=1, now=NOW)
    with pytest.raises(StalePolicyVersion):
        repo.update(mine)


def test_list_all_orders_by_name(repo: TableMaintenancePoliciesSqlRepo):
    """Policies are listed ordered by name."""
    repo.create(_policy("b"))
    repo.create(_policy("a"))
    assert [p.name.value for p in repo.list_all()] == ["a", "b"]


def test_delete_removes_versions_too(repo: TableMaintenancePoliciesSqlRepo):
    """Deleting a policy deletes its versions."""
    policy = _policy()
    repo.create(policy)
    policy.replace(MaintenancePolicyContent.platform_default(), expected_version=1, now=NOW)
    repo.update(policy)
    repo.delete(policy.id)
    assert repo.get(policy.id) is None
    assert repo.get_version(policy.id, 1) is None
    assert repo.get_version(policy.id, 2) is None


def _engine_enforcing_foreign_keys() -> Engine:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    event.listen(engine, "connect", lambda dbapi_connection, _: dbapi_connection.execute("PRAGMA foreign_keys=ON"))
    create_schema(engine)
    return engine


def test_delete_of_a_policy_attached_meanwhile_conflicts():
    """An attachment landing after the delete's check makes the delete a ConflictError and keeps the policy."""
    engine = _engine_enforcing_foreign_keys()
    repo = TableMaintenancePoliciesSqlRepo(engine)
    policy = _policy()
    repo.create(policy)
    target = PolicyTarget(type=PolicyTargetType.CATALOG, path=("prod",))
    TableMaintenancePolicyAttachmentsSqlRepo(engine).create(
        TableMaintenancePolicyAttachment.attach(target, policy.id, NOW)
    )
    with pytest.raises(ConflictError):
        repo.delete(policy.id)
    assert repo.get(policy.id) is not None
    assert repo.get_version(policy.id, 1) is not None
