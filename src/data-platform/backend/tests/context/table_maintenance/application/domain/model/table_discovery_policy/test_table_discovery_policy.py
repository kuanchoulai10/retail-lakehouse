"""Test the TableDiscoveryPolicy aggregate: versions, the fixed default, rule ids and decisions."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from base import InvariantViolation
from context.table_maintenance.application.domain.model.table import TableName
from context.table_maintenance.application.domain.model.table_discovery_policy import (
    DEFAULT_DISCOVERY_POLICY_ID,
    DEFAULT_DISCOVERY_POLICY_NAME,
    DefaultDiscoveryPolicyIsFixed,
    DiscoveryDecision,
    DiscoveryMatch,
    DiscoveryOutcome,
    DiscoveryPolicyContent,
    StaleDiscoveryPolicyVersion,
    TableDiscoveryPolicy,
    TableDiscoveryPolicyId,
    TableDiscoveryPolicyName,
    TableDiscoveryPolicyVersion,
    TableDiscoveryRuleId,
    UnknownDiscoveryRuleId,
)
from shared_kernel import prefixed_id_pattern

R1, R2 = "dr-00000000000000000000000001", "dr-00000000000000000000000002"
RID1, RID2 = TableDiscoveryRuleId(R1), TableDiscoveryRuleId(R2)
ORDERS = TableName(catalog="iceberg", namespace="sales.eu", table="orders_tmp")
NAME = TableDiscoveryPolicyName(value="sales-tables")
T0 = datetime(2026, 11, 1, tzinfo=UTC)
T1 = T0 + timedelta(hours=1)


def _rule(rule_id: str, outcome: str, **globs: list[str]) -> dict[str, Any]:
    """Return a rule in its wire form, one glob condition per keyword (``namespace``, ``table_name``)."""
    return {
        "id": rule_id,
        "outcome": outcome,
        "conditions": [
            {"attribute": attribute, "operator": "glob", "values": values} for attribute, values in globs.items()
        ],
    }


def _content(no_match: str = "unmanage", *rules: dict[str, Any]) -> DiscoveryPolicyContent:
    return DiscoveryPolicyContent.from_primitives({"no_match_outcome": no_match, "rules": list(rules)})


def test_create_starts_at_version_one_under_a_new_dp_id():
    """A new policy gets a random ``dp-`` id of its own, at version 1, with equal timestamps."""
    first = TableDiscoveryPolicy.create(NAME, _content(), T0)
    second = TableDiscoveryPolicy.create(NAME, _content(), T0)

    assert prefixed_id_pattern("dp").fullmatch(first.id.value)
    assert first.id != second.id
    assert (first.name, first.version, first.created_at, first.updated_at) == (NAME, 1, T0, T0)
    assert not first.is_default


def test_create_accepts_the_rule_ids_the_caller_issued():
    """A create may name only the rule ids issued for this request."""
    content = _content("unmanage", _rule(R1, "manage", table_name=["*"]))

    policy = TableDiscoveryPolicy.create(NAME, content, T0, new_rule_ids={RID1})

    assert policy.content == content


def test_create_refuses_any_rule_id():
    """A create without issued ids refuses every rule id, so a client cannot choose one."""
    with pytest.raises(UnknownDiscoveryRuleId, match=f"unknown discovery rule id {R1}"):
        TableDiscoveryPolicy.create(NAME, _content("unmanage", _rule(R1, "manage", table_name=["*"])), T0)


def test_create_refuses_a_rule_id_it_was_not_issued():
    """An issued id does not let through another one."""
    content = _content("unmanage", _rule(R1, "manage", table_name=["a"]), _rule(R2, "manage", table_name=["b"]))

    with pytest.raises(UnknownDiscoveryRuleId, match=R2):
        TableDiscoveryPolicy.create(NAME, content, T0, new_rule_ids={RID1})


def test_the_first_matching_rule_decides():
    """The deciding rule's outcome decides, recorded with the policy's id, version and the rule's id."""
    policy = TableDiscoveryPolicy.create(NAME, _content("unmanage"), T0)
    policy.replace(
        _content(
            "unmanage",
            _rule(R1, "manage", table_name=["orders_tmp"]),
            _rule(R2, "unmanage", table_name=["*_tmp"]),
        ),
        1,
        T1,
        new_rule_ids={RID1, RID2},
    )

    assert policy.decide(ORDERS) == DiscoveryDecision(
        outcome=DiscoveryOutcome.MANAGE, match=DiscoveryMatch(policy_id=policy.id, policy_version=2, rule_id=RID1)
    )


def test_a_deciding_unmanage_rule_wins_over_a_managing_no_match_outcome():
    """A matching rule decides even when the no-match outcome says otherwise."""
    policy = TableDiscoveryPolicy.create(
        NAME, _content("manage", _rule(R1, "unmanage", table_name=["*_tmp"])), T0, new_rule_ids={RID1}
    )

    decision = policy.decide(ORDERS)

    assert decision.outcome is DiscoveryOutcome.UNMANAGE
    assert decision.match.rule_id == RID1
    assert not decision.manages


def test_no_match_uses_the_no_match_outcome_without_a_rule():
    """When no rule matches, the no-match outcome decides and no rule is recorded."""
    policy = TableDiscoveryPolicy.create(NAME, _content("manage"), T0)

    decision = policy.decide(ORDERS)

    assert decision == DiscoveryDecision(
        outcome=DiscoveryOutcome.MANAGE, match=DiscoveryMatch(policy_id=policy.id, policy_version=1, rule_id=None)
    )
    assert decision.manages


def test_no_match_falls_back_when_the_rules_miss():
    """Rules that all miss leave the decision to the no-match outcome."""
    policy = TableDiscoveryPolicy.create(
        NAME, _content("unmanage", _rule(R1, "manage", table_name=["customers"])), T0, new_rule_ids={RID1}
    )

    assert policy.decide(ORDERS) == DiscoveryDecision(
        outcome=DiscoveryOutcome.UNMANAGE, match=DiscoveryMatch(policy_id=policy.id, policy_version=1, rule_id=None)
    )


def test_replace_makes_the_next_version():
    """A replacement from the current version bumps the version and the update time."""
    policy = TableDiscoveryPolicy.create(NAME, _content(), T0)
    content = _content("manage")

    policy.replace(content, 1, T1)

    assert (policy.content, policy.version, policy.created_at, policy.updated_at) == (content, 2, T0, T1)
    assert policy.current_version() == TableDiscoveryPolicyVersion(
        policy_id=policy.id, version=2, content=content, created_at=T1
    )


def test_replace_keeps_the_rule_ids_of_the_current_version():
    """An update may name the ids the policy holds without issuing them again."""
    policy = TableDiscoveryPolicy.create(
        NAME, _content("unmanage", _rule(R1, "manage", table_name=["a"])), T0, new_rule_ids={RID1}
    )

    policy.replace(_content("unmanage", _rule(R1, "unmanage", table_name=["b"])), 1, T1)

    assert policy.content.rule_ids() == frozenset({RID1})


def test_replace_refuses_an_id_the_policy_does_not_hold():
    """An id that is neither in the current version nor issued for this request is refused, and nothing changes."""
    policy = TableDiscoveryPolicy.create(NAME, _content(), T0)

    with pytest.raises(UnknownDiscoveryRuleId, match=R2):
        policy.replace(_content("unmanage", _rule(R2, "manage", table_name=["*"])), 1, T1)

    assert policy.version == 1


def test_replace_refuses_an_id_only_an_older_version_held():
    """Only the current version's ids may be named: a removed rule cannot come back by id."""
    policy = TableDiscoveryPolicy.create(
        NAME, _content("unmanage", _rule(R1, "manage", table_name=["a"])), T0, new_rule_ids={RID1}
    )
    policy.replace(_content(), 1, T1)

    with pytest.raises(UnknownDiscoveryRuleId, match=R1):
        policy.replace(_content("unmanage", _rule(R1, "manage", table_name=["a"])), 2, T1)


def test_replace_refuses_a_stale_version():
    """A replacement from a version that is not the current one is refused, and nothing changes."""
    policy = TableDiscoveryPolicy.create(NAME, _content(), T0)

    with pytest.raises(StaleDiscoveryPolicyVersion, match="sales-tables is at version 1, not 3"):
        policy.replace(_content("manage"), 3, T1)

    assert (policy.version, policy.content) == (1, _content())


def test_replace_refuses_an_older_version():
    """A save based on a version older than the current one is refused, and nothing changes."""
    policy = TableDiscoveryPolicy.create(NAME, _content(), T0)
    policy.replace(_content("manage"), 1, T1)

    with pytest.raises(StaleDiscoveryPolicyVersion, match="sales-tables is at version 2, not 1"):
        policy.replace(_content("unmanage"), 1, T1)

    assert (policy.version, policy.content) == (2, _content("manage"))


def test_a_stale_version_is_reported_before_an_unknown_rule_id():
    """A stale request is a conflict whatever its content holds."""
    policy = TableDiscoveryPolicy.create(NAME, _content(), T0)

    with pytest.raises(StaleDiscoveryPolicyVersion):
        policy.replace(_content("unmanage", _rule(R2, "manage", table_name=["*"])), 3, T1)


def test_the_default_cannot_be_replaced():
    """The platform default is fixed: even a current, valid replacement is refused first."""
    policy = TableDiscoveryPolicy.create_default(T0)

    with pytest.raises(DefaultDiscoveryPolicyIsFixed):
        policy.replace(_content("manage"), 3, T1)

    assert (policy.version, policy.content) == (1, DiscoveryPolicyContent.platform_default())


def test_the_default_has_its_fixed_id_name_and_content():
    """The default has the fixed ``dp-`` id, the name ``default``, no rules and the ``unmanage`` outcome."""
    policy = TableDiscoveryPolicy.create_default(T0)

    assert DEFAULT_DISCOVERY_POLICY_ID == TableDiscoveryPolicyId("dp-00000000000000000000000000")
    assert policy.is_default
    assert policy.id == DEFAULT_DISCOVERY_POLICY_ID
    assert policy.name == TableDiscoveryPolicyName(value=DEFAULT_DISCOVERY_POLICY_NAME)
    assert DEFAULT_DISCOVERY_POLICY_NAME == "default"
    assert policy.content == DiscoveryPolicyContent.platform_default()
    assert policy.content.rules == ()
    assert policy.content.no_match_outcome is DiscoveryOutcome.UNMANAGE
    assert policy.content.description.startswith("Manages nothing.")
    assert (policy.version, policy.created_at, policy.updated_at) == (1, T0, T0)


def test_the_default_decides_unmanage_at_version_one():
    """The default unmanages every table, recorded as the default at version 1 with no rule."""
    assert TableDiscoveryPolicy.create_default(T0).decide(ORDERS) == DiscoveryDecision(
        outcome=DiscoveryOutcome.UNMANAGE,
        match=DiscoveryMatch(policy_id=DEFAULT_DISCOVERY_POLICY_ID, policy_version=1, rule_id=None),
    )


def test_a_policy_named_default_is_not_the_default():
    """The default is told by its fixed id, not by its name."""
    policy = TableDiscoveryPolicy.create(TableDiscoveryPolicyName(value=DEFAULT_DISCOVERY_POLICY_NAME), _content(), T0)

    assert not policy.is_default


def test_can_manage_delegates_to_the_content():
    """A policy could manage a table exactly when its content could."""
    assert not TableDiscoveryPolicy.create_default(T0).can_manage()
    assert TableDiscoveryPolicy.create(NAME, _content("manage"), T0).can_manage()


def test_policy_id_refuses_another_shape():
    """A policy id must look like ``dp-<26 base32 characters>``."""
    with pytest.raises(InvariantViolation, match="TableDiscoveryPolicyId must look like dp-"):
        TableDiscoveryPolicyId("sales-tables")


@pytest.mark.parametrize("name", ["has space", "", "x" * 65, "a/b", "dp-00000000000000000000000000"])
def test_invalid_name_is_rejected(name: str):
    """A name outside the policy name rule, or shaped like a prefixed id, is refused."""
    with pytest.raises(InvariantViolation):
        TableDiscoveryPolicyName(value=name)


def test_the_errors_are_value_errors_of_their_own():
    """A stale version and a change to the default are conflicts; an unknown rule id is an invalid request."""
    for error in (StaleDiscoveryPolicyVersion, DefaultDiscoveryPolicyIsFixed, UnknownDiscoveryRuleId):
        assert issubclass(error, ValueError)
    assert not issubclass(UnknownDiscoveryRuleId, StaleDiscoveryPolicyVersion | DefaultDiscoveryPolicyIsFixed)
