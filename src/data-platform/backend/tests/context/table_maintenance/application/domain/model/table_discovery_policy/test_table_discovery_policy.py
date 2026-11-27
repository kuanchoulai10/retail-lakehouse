"""Test the TableDiscoveryPolicy aggregate: versions and the decision its rules make."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from base import InvariantViolation
from context.table_maintenance.application.domain.model.shared import TableDiscoveryPolicyId
from context.table_maintenance.application.domain.model.table import TableName
from context.table_maintenance.application.domain.model.table_discovery_policy import (
    DecidedBy,
    DiscoveryRule,
    DiscoveryRules,
    ManagementDecision,
    RuleAction,
    StaleDiscoveryPolicyVersion,
    TableDiscoveryPolicy,
    TableDiscoveryPolicyName,
    TableDiscoveryPolicyVersion,
    TableNamePattern,
)
from tests.context.table_maintenance.id_shape import IdShape

NAME = TableDiscoveryPolicyName(value="sales-tables")
T0 = datetime(2026, 11, 1, tzinfo=UTC)
T1 = T0 + timedelta(hours=1)
REFUNDS_TMP = TableName(catalog="lakehouse", namespace="sales", table="refunds_tmp")
ORDERS = TableName(catalog="lakehouse", namespace="sales", table="orders")


def _rules(*specs: tuple[RuleAction, str]) -> DiscoveryRules:
    return DiscoveryRules(
        rules=tuple(
            DiscoveryRule(action=action, table_name_pattern=TableNamePattern(value=pattern))
            for action, pattern in specs
        )
    )


INCLUDE_ALL = _rules((RuleAction.INCLUDE, "*"))
INCLUDE_ALL_BUT_TMP = _rules((RuleAction.INCLUDE, "*"), (RuleAction.EXCLUDE, "*_tmp"))


def test_create_starts_at_version_one_under_a_new_dp_id():
    """A new policy gets a random ``dp-`` id of its own, at version 1, with equal timestamps."""
    first = TableDiscoveryPolicy.create(NAME, "orders only", INCLUDE_ALL, T0)
    second = TableDiscoveryPolicy.create(NAME, "", INCLUDE_ALL, T0)

    assert IdShape(TableDiscoveryPolicyId).fullmatch(first.id.value)
    assert first.id != second.id
    assert (first.name, first.description, first.rules, first.version) == (NAME, "orders only", INCLUDE_ALL, 1)
    assert (first.created_at, first.updated_at) == (T0, T0)


def test_revise_with_the_current_version_makes_the_next_version():
    """A revision from the current version holds the new rules and description at version 2."""
    policy = TableDiscoveryPolicy.create(NAME, "", INCLUDE_ALL, T0)

    policy.revise("no temporary tables", INCLUDE_ALL_BUT_TMP, 1, T1)

    assert (policy.description, policy.rules, policy.version) == ("no temporary tables", INCLUDE_ALL_BUT_TMP, 2)
    assert (policy.created_at, policy.updated_at) == (T0, T1)


def test_revise_with_a_stale_version_is_refused():
    """A revision from a version that is not the current one is refused, and nothing changes."""
    policy = TableDiscoveryPolicy.create(NAME, "", INCLUDE_ALL, T0)
    policy.revise("", INCLUDE_ALL_BUT_TMP, 1, T1)

    with pytest.raises(StaleDiscoveryPolicyVersion, match="sales-tables is at version 2, not 1"):
        policy.revise("again", INCLUDE_ALL, 1, T1)

    assert (policy.description, policy.rules, policy.version) == ("", INCLUDE_ALL_BUT_TMP, 2)


def test_revise_with_a_future_version_is_refused():
    """A revision from a version the policy never reached is refused too."""
    policy = TableDiscoveryPolicy.create(NAME, "", INCLUDE_ALL, T0)

    with pytest.raises(StaleDiscoveryPolicyVersion, match="sales-tables is at version 1, not 3"):
        policy.revise("", INCLUDE_ALL_BUT_TMP, 3, T1)

    assert policy.version == 1


def test_the_last_matching_rule_decides_and_is_recorded_by_position():
    """Under ``[include *, exclude *_tmp]`` a ``_tmp`` table is excluded by rule 2."""
    policy = TableDiscoveryPolicy.create(NAME, "", INCLUDE_ALL_BUT_TMP, T0)

    assert policy.should_manage(REFUNDS_TMP) == ManagementDecision(
        manage=False, decided_by=DecidedBy(policy_id=policy.id, policy_version=1, rule_position=2)
    )


def test_an_included_table_is_managed_by_its_rule():
    """A table only the include rule matches is managed, decided by rule 1."""
    policy = TableDiscoveryPolicy.create(NAME, "", INCLUDE_ALL_BUT_TMP, T0)

    assert policy.should_manage(ORDERS) == ManagementDecision(
        manage=True, decided_by=DecidedBy(policy_id=policy.id, policy_version=1, rule_position=1)
    )


def test_a_table_no_rule_matches_is_not_managed_and_names_no_rule():
    """When no rule matches, the policy still decides: not managed, with no rule position."""
    policy = TableDiscoveryPolicy.create(NAME, "", _rules((RuleAction.INCLUDE, "customers")), T0)

    assert policy.should_manage(ORDERS) == ManagementDecision(
        manage=False, decided_by=DecidedBy(policy_id=policy.id, policy_version=1, rule_position=None)
    )


def test_the_decision_names_the_current_version():
    """A decision after a revision names the version that made it."""
    policy = TableDiscoveryPolicy.create(NAME, "", INCLUDE_ALL, T0)
    policy.revise("", INCLUDE_ALL_BUT_TMP, 1, T1)

    decided_by = policy.should_manage(ORDERS).decided_by

    assert decided_by is not None
    assert decided_by.policy_version == 2


def test_the_pattern_matches_the_table_name_only():
    """A pattern never matches the namespace or catalog part of the name."""
    policy = TableDiscoveryPolicy.create(NAME, "", _rules((RuleAction.INCLUDE, "sales*")), T0)

    assert not policy.should_manage(ORDERS).manage


def test_current_version_holds_the_description_and_rules():
    """The version record is the policy's current description and rules, stamped with its update time."""
    policy = TableDiscoveryPolicy.create(NAME, "", INCLUDE_ALL, T0)
    policy.revise("no temporary tables", INCLUDE_ALL_BUT_TMP, 1, T1)

    assert policy.current_version() == TableDiscoveryPolicyVersion(
        policy_id=policy.id, version=2, description="no temporary tables", rules=INCLUDE_ALL_BUT_TMP, created_at=T1
    )


def test_policy_id_refuses_another_shape():
    """A policy id must look like ``dp-<26 base32 characters>``."""
    with pytest.raises(InvariantViolation, match="TableDiscoveryPolicyId must look like dp-"):
        TableDiscoveryPolicyId("sales-tables")


@pytest.mark.parametrize("name", ["has space", "", "x" * 65, "a/b", "dp-00000000000000000000000000"])
def test_invalid_name_is_rejected(name: str):
    """A name outside the policy name rule, or shaped like a prefixed id, is refused."""
    with pytest.raises(InvariantViolation):
        TableDiscoveryPolicyName(value=name)


def test_a_stale_version_is_a_value_error():
    """A stale version is a conflict of its own, a ``ValueError``."""
    assert issubclass(StaleDiscoveryPolicyVersion, ValueError)


def test_an_exclude_only_policy_cannot_include():
    """A policy whose rules all exclude can include no table."""
    assert not TableDiscoveryPolicy.create(NAME, "", _rules((RuleAction.EXCLUDE, "*")), T0).can_include()


def test_a_policy_with_an_include_rule_can_include():
    """A policy with an include rule, even followed by an exclude, can include a table."""
    assert TableDiscoveryPolicy.create(NAME, "", INCLUDE_ALL_BUT_TMP, T0).can_include()
