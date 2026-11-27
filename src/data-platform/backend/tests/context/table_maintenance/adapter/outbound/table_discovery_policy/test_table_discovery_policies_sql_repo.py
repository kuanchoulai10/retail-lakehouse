"""Test the repositories of the TableDiscoveryPolicy aggregate, the SQL one and the in-memory fake alike."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool

from context.table_maintenance.adapter.outbound.shared.sql import create_schema
from context.table_maintenance.adapter.outbound.table_discovery_policy.sql import (
    TableDiscoveryPoliciesSqlRepo,
    table_discovery_policy_versions_table,
)
from context.table_maintenance.adapter.outbound.table_discovery_policy_attachment.sql import (
    TableDiscoveryPolicyAttachmentsSqlRepo,
)
from context.table_maintenance.application.domain.model.shared import (
    PolicyTarget,
    PolicyTargetType,
    TableDiscoveryPolicyId,
)
from context.table_maintenance.application.domain.model.table_discovery_policy import (
    DiscoveryRule,
    DiscoveryRules,
    RuleAction,
    StaleDiscoveryPolicyVersion,
    TableDiscoveryPolicy,
    TableDiscoveryPolicyName,
    TableNamePattern,
)
from context.table_maintenance.application.domain.model.table_discovery_policy_attachment import (
    TableDiscoveryPolicyAttachment,
)
from context.table_maintenance.application.exceptions import ConflictError
from tests.context.table_maintenance.fakes.in_memory_table_discovery_policies_repo import (
    InMemoryTableDiscoveryPoliciesRepo,
)
from tests.context.table_maintenance.fakes.in_memory_table_discovery_policy_attachments_repo import (
    InMemoryTableDiscoveryPolicyAttachmentsRepo,
)

if TYPE_CHECKING:
    from sqlalchemy import Engine

    from context.table_maintenance.application.port.outbound.table_discovery_policy import (
        TableDiscoveryPoliciesRepo,
    )
    from context.table_maintenance.application.port.outbound.table_discovery_policy_attachment import (
        TableDiscoveryPolicyAttachmentsRepo,
    )

NOW = datetime(2026, 11, 1, tzinfo=UTC)


def _rules(*specs: tuple[RuleAction, str]) -> DiscoveryRules:
    return DiscoveryRules(
        rules=tuple(
            DiscoveryRule(action=action, table_name_pattern=TableNamePattern(value=pattern))
            for action, pattern in specs
        )
    )


SALES_ORDERS = _rules((RuleAction.INCLUDE, "orders_*"), (RuleAction.EXCLUDE, "orders_tmp*"))
EVERYTHING = _rules((RuleAction.INCLUDE, "*"))


def _engine_enforcing_foreign_keys() -> Engine:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    event.listen(engine, "connect", lambda dbapi_connection, _: dbapi_connection.execute("PRAGMA foreign_keys=ON"))
    create_schema(engine)
    return engine


@pytest.fixture(params=["sql", "memory"])
def repo(request: pytest.FixtureRequest, engine: Engine) -> TableDiscoveryPoliciesRepo:
    """Provide each discovery policies repository implementation."""
    if request.param == "sql":
        return TableDiscoveryPoliciesSqlRepo(engine)
    return InMemoryTableDiscoveryPoliciesRepo()


@pytest.fixture(params=["sql", "memory"])
def repos(request: pytest.FixtureRequest) -> tuple[TableDiscoveryPoliciesRepo, TableDiscoveryPolicyAttachmentsRepo]:
    """Provide a policies and an attachments repository that share storage, so an attachment pins its policy."""
    if request.param == "sql":
        engine = _engine_enforcing_foreign_keys()
        return TableDiscoveryPoliciesSqlRepo(engine), TableDiscoveryPolicyAttachmentsSqlRepo(engine)
    attachments = InMemoryTableDiscoveryPolicyAttachmentsRepo()
    return InMemoryTableDiscoveryPoliciesRepo(attachments=attachments), attachments


def _policy(name: str = "sales", rules: DiscoveryRules = SALES_ORDERS) -> TableDiscoveryPolicy:
    return TableDiscoveryPolicy.create(TableDiscoveryPolicyName(value=name), "sales tables", rules, NOW)


def test_a_created_policy_loads_back_equal_by_id_and_by_name(repo: TableDiscoveryPoliciesRepo):
    """Every field of a created policy, its description and its rules in order included, reads back by id and name."""
    policy = _policy()
    repo.create(policy)

    loaded = repo.get(policy.id)

    assert loaded == policy
    assert loaded is not None
    assert loaded.created_at.tzinfo is not None
    assert repo.get_by_name(TableDiscoveryPolicyName(value="sales")) == policy
    assert repo.get_by_name(TableDiscoveryPolicyName(value="nope")) is None
    assert repo.get(TableDiscoveryPolicyId.new()) is None


def test_create_writes_the_first_version(repo: TableDiscoveryPoliciesRepo):
    """A created policy has its version 1 readable, holding its description and rules."""
    policy = _policy()
    repo.create(policy)

    first = repo.get_version(policy.id, 1)

    assert first is not None
    assert first.policy_id == policy.id
    assert (first.description, first.rules) == ("sales tables", SALES_ORDERS)
    assert first.created_at == NOW


def test_update_writes_a_version_and_keeps_the_old_one(repo: TableDiscoveryPoliciesRepo):
    """A revision stored by ``update`` is the current version, and v1 and v2 are both readable."""
    policy = _policy()
    repo.create(policy)
    policy.revise("everything", EVERYTHING, expected_version=1, now=NOW + timedelta(hours=1))

    repo.update(policy)

    loaded = repo.get(policy.id)
    assert loaded is not None
    assert (loaded.version, loaded.description, loaded.rules) == (2, "everything", EVERYTHING)
    assert (loaded.created_at, loaded.updated_at) == (NOW, NOW + timedelta(hours=1))
    v1, v2 = repo.get_version(policy.id, 1), repo.get_version(policy.id, 2)
    assert v1 is not None
    assert (v1.description, v1.rules) == ("sales tables", SALES_ORDERS)
    assert v2 is not None
    assert (v2.description, v2.rules, v2.created_at) == ("everything", EVERYTHING, NOW + timedelta(hours=1))
    assert repo.get_version(policy.id, 3) is None


def test_update_from_a_stale_copy_is_refused(repo: TableDiscoveryPoliciesRepo):
    """Two copies revised from version 1: the second ``update`` is refused and the first one's rules stay."""
    policy = _policy()
    repo.create(policy)
    first, second = repo.get(policy.id), repo.get(policy.id)
    assert first is not None
    assert second is not None
    first.revise("", EVERYTHING, expected_version=1, now=NOW)
    repo.update(first)
    second.revise("", SALES_ORDERS, expected_version=1, now=NOW)

    with pytest.raises(StaleDiscoveryPolicyVersion):
        repo.update(second)

    loaded = repo.get(policy.id)
    assert loaded is not None
    assert (loaded.version, loaded.rules) == (2, EVERYTHING)
    assert repo.get_version(policy.id, 3) is None


def test_update_of_an_unknown_policy_raises_lookup_error(repo: TableDiscoveryPoliciesRepo):
    """Updating a policy that was never stored is a LookupError, not a stale version."""
    policy = _policy()
    policy.revise("", EVERYTHING, expected_version=1, now=NOW)

    with pytest.raises(LookupError):
        repo.update(policy)


def test_a_taken_name_conflicts(repo: TableDiscoveryPoliciesRepo):
    """A second policy with a taken name raises ConflictError, though its id is new, and is not stored."""
    repo.create(_policy())
    other = _policy()

    with pytest.raises(ConflictError):
        repo.create(other)

    assert repo.get(other.id) is None


def test_get_many_returns_the_existing_ones(repo: TableDiscoveryPoliciesRepo):
    """``get_many`` returns the policies that exist among the ids, skipping unknown ones."""
    sales, everything = _policy("sales"), _policy("everything", EVERYTHING)
    repo.create(sales)
    repo.create(everything)

    found = repo.get_many([sales.id, TableDiscoveryPolicyId.new(), everything.id])

    assert sorted(p.name.value for p in found) == ["everything", "sales"]
    assert repo.get_many([]) == []


def test_list_all_orders_by_name(repo: TableDiscoveryPoliciesRepo):
    """Policies are listed ordered by name, at their current version."""
    repo.create(_policy("b"))
    repo.create(_policy("a"))

    assert [p.name.value for p in repo.list_all()] == ["a", "b"]


def test_delete_removes_the_versions_too(repo: TableDiscoveryPoliciesRepo):
    """Deleting a policy deletes it and every one of its versions."""
    policy = _policy()
    repo.create(policy)
    policy.revise("", EVERYTHING, expected_version=1, now=NOW)
    repo.update(policy)

    repo.delete(policy.id)

    assert repo.get(policy.id) is None
    assert repo.get_version(policy.id, 1) is None
    assert repo.get_version(policy.id, 2) is None


def test_delete_while_attached_conflicts(
    repos: tuple[TableDiscoveryPoliciesRepo, TableDiscoveryPolicyAttachmentsRepo],
):
    """A policy attached anywhere is not deleted: ConflictError, and the policy and its version stay."""
    policies, attachments = repos
    policy = _policy()
    policies.create(policy)
    target = PolicyTarget(type=PolicyTargetType.CATALOG, path=("prod",))
    attachments.create(TableDiscoveryPolicyAttachment.attach(target, policy.id, NOW))

    with pytest.raises(ConflictError):
        policies.delete(policy.id)

    assert policies.get(policy.id) is not None
    assert policies.get_version(policy.id, 1) is not None


def test_a_version_is_stored_as_its_description_and_rules(engine: Engine):
    """A version row holds ``{"description", "rules": [{"action", "table_name_pattern"}]}``, in rule order."""
    policy = _policy()
    TableDiscoveryPoliciesSqlRepo(engine).create(policy)

    with engine.connect() as connection:
        row = connection.execute(table_discovery_policy_versions_table.select()).mappings().one()

    assert row["content_json"] == {
        "description": "sales tables",
        "rules": [
            {"action": "include", "table_name_pattern": "orders_*"},
            {"action": "exclude", "table_name_pattern": "orders_tmp*"},
        ],
    }
