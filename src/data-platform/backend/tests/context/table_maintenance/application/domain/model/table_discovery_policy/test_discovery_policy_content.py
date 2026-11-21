"""Test DiscoveryPolicyContent: its rules, its conditions and its wire form."""

from __future__ import annotations

from typing import Any

import pytest

from base import InvariantViolation
from context.table_maintenance.application.domain.model.table import TableName
from context.table_maintenance.application.domain.model.table_discovery_policy import (
    ConditionOperator,
    DiscoveryAttribute,
    DiscoveryCondition,
    DiscoveryOutcome,
    DiscoveryPolicyContent,
    TableDiscoveryRule,
    TableDiscoveryRuleId,
)

R1, R2 = "dr-00000000000000000000000001", "dr-00000000000000000000000002"
RID1, RID2 = TableDiscoveryRuleId(R1), TableDiscoveryRuleId(R2)
ORDERS = TableName(catalog="iceberg", namespace="sales.eu", table="orders_tmp")


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


def test_the_first_matching_rule_decides():
    """Rules are read top to bottom and the first whose conditions all hold decides."""
    content = _content(
        "unmanage",
        _rule(R1, "manage", table_name=["orders_tmp"]),
        _rule(R2, "unmanage", table_name=["*_tmp"]),
    )

    deciding = content.deciding_rule(ORDERS)

    assert deciding is not None
    assert (deciding.id, deciding.outcome) == (RID1, DiscoveryOutcome.MANAGE)


def test_a_later_rule_decides_when_the_earlier_ones_miss():
    """A rule that does not match is passed over for the next one."""
    content = _content(
        "unmanage",
        _rule(R1, "manage", table_name=["customers"]),
        _rule(R2, "unmanage", table_name=["*_tmp"]),
    )

    deciding = content.deciding_rule(ORDERS)

    assert deciding is not None
    assert deciding.id == RID2


def test_no_rule_decides_when_none_matches():
    """With no matching rule there is no deciding rule; the no-match outcome is the policy's to apply."""
    assert _content("manage", _rule(R1, "manage", table_name=["customers"])).deciding_rule(ORDERS) is None
    assert _content("manage").deciding_rule(ORDERS) is None


def test_every_condition_must_hold():
    """A rule matches only when each of its conditions holds."""
    missing_namespace = TableDiscoveryRule.from_primitives(
        _rule(R1, "manage", namespace=["sales"], table_name=["orders_*"])
    )
    both_hold = TableDiscoveryRule.from_primitives(_rule(R1, "manage", namespace=["sales.eu"], table_name=["orders_*"]))
    missing_table = TableDiscoveryRule.from_primitives(_rule(R1, "manage", namespace=["sales.eu"], table_name=["x"]))

    assert not missing_namespace.matches(ORDERS)
    assert not missing_table.matches(ORDERS)
    assert both_hold.matches(ORDERS)


def test_a_condition_holds_when_any_of_its_values_matches():
    """The values of one condition are alternatives."""
    condition = DiscoveryCondition(
        attribute=DiscoveryAttribute.TABLE_NAME, operator=ConditionOperator.GLOB, values=("customers", "orders_*")
    )

    assert condition.matches(ORDERS)


def test_namespace_glob_crosses_dots():
    """A namespace glob matches the dot-joined namespace, and ``*`` crosses dots."""
    condition = DiscoveryCondition(
        attribute=DiscoveryAttribute.NAMESPACE, operator=ConditionOperator.GLOB, values=("sales.*",)
    )
    deep = ORDERS.with_changes(namespace="sales.eu.west")

    assert condition.matches(ORDERS)
    assert condition.matches(deep)
    assert not condition.with_changes(values=("sales",)).matches(ORDERS)


def test_table_name_condition_reads_the_table_name_only():
    """A ``table_name`` condition never reads the namespace or the catalog."""
    condition = DiscoveryCondition(
        attribute=DiscoveryAttribute.TABLE_NAME, operator=ConditionOperator.GLOB, values=("sales*",)
    )

    assert not condition.matches(ORDERS)


def test_glob_is_case_sensitive():
    """Globs match case-sensitively."""
    condition = DiscoveryCondition(
        attribute=DiscoveryAttribute.TABLE_NAME, operator=ConditionOperator.GLOB, values=("Orders*",)
    )

    assert not condition.matches(ORDERS)


def test_a_rule_needs_a_condition():
    """A rule without a condition is refused."""
    with pytest.raises(InvariantViolation, match="at least one condition"):
        _content("unmanage", {"id": R1, "outcome": "manage", "conditions": []})


def test_an_attribute_appears_once_per_rule():
    """Two conditions on the same attribute in one rule are refused."""
    rule = _rule(R1, "manage", table_name=["orders_*"])
    rule["conditions"].append({"attribute": "table_name", "operator": "glob", "values": ["*_tmp"]})

    with pytest.raises(InvariantViolation, match="table_name appears more than once"):
        _content("unmanage", rule)


@pytest.mark.parametrize(("values", "message"), [([], "at least one value"), ([""], "must not be empty")])
def test_empty_values_or_an_empty_glob_are_refused(values: list[str], message: str):
    """A condition needs at least one value, and no value may be empty."""
    with pytest.raises(InvariantViolation, match=message):
        _content("unmanage", _rule(R1, "manage", table_name=values))


@pytest.mark.parametrize(
    "condition",
    [
        {"attribute": "label", "operator": "glob", "values": ["x"]},
        {"attribute": "table_name", "operator": "regex", "values": ["x"]},
    ],
)
def test_unknown_attribute_or_operator_is_refused(condition: dict[str, Any]):
    """Only the known attributes and operators are accepted."""
    with pytest.raises(InvariantViolation):
        _content("unmanage", {"id": R1, "outcome": "manage", "conditions": [condition]})


def test_unknown_outcome_is_refused():
    """A rule and the no-match outcome are ``manage`` or ``unmanage``."""
    with pytest.raises(InvariantViolation):
        _content("include")
    with pytest.raises(InvariantViolation):
        _content("unmanage", _rule(R1, "include", table_name=["*"]))


def test_rule_ids_are_unique():
    """The same rule id twice in one content is refused."""
    with pytest.raises(InvariantViolation, match=f"discovery rule {R1} appears more than once"):
        _content("unmanage", _rule(R1, "manage", table_name=["a"]), _rule(R1, "unmanage", table_name=["b"]))


def test_a_rule_id_is_a_dr_id():
    """A rule id that is not a ``dr-`` id is refused."""
    with pytest.raises(InvariantViolation):
        _content("unmanage", _rule("", "manage", table_name=["*"]))


def test_can_manage():
    """It holds when a rule manages or the no-match outcome does, even behind a catch-all unmanage rule."""
    assert not DiscoveryPolicyContent.platform_default().can_manage()
    assert _content("unmanage", _rule(R1, "manage", table_name=["*"])).can_manage()
    assert _content("manage").can_manage()
    assert not _content("unmanage", _rule(R1, "unmanage", table_name=["*"])).can_manage()
    assert _content(
        "unmanage", _rule(R1, "unmanage", table_name=["*"]), _rule(R2, "manage", table_name=["orders_*"])
    ).can_manage()


def test_rule_ids():
    """The content names the ids of its rules."""
    content = _content("unmanage", _rule(R1, "manage", table_name=["a"]), _rule(R2, "unmanage", table_name=["b"]))

    assert content.rule_ids() == frozenset({RID1, RID2})
    assert _content().rule_ids() == frozenset()


def test_platform_default_manages_nothing():
    """The default content has no rules, unmanages every table and says so."""
    content = DiscoveryPolicyContent.platform_default()

    assert content.rules == ()
    assert content.no_match_outcome is DiscoveryOutcome.UNMANAGE
    assert content.description == (
        "Manages nothing. Attach another discovery policy to a catalog, namespace or table to manage its tables."
    )


def test_description_defaults_to_empty():
    """A content without a description has an empty one."""
    assert _content().description == ""


def test_content_round_trips_its_wire_form():
    """The wire form reads back to the same primitives, in the shape of Kubernetes ``matchExpressions``."""
    wire = {
        "description": "sales tables",
        "no_match_outcome": "unmanage",
        "rules": [
            {
                "id": R1,
                "outcome": "manage",
                "conditions": [
                    {"attribute": "namespace", "operator": "glob", "values": ["sales", "sales.*"]},
                    {"attribute": "table_name", "operator": "glob", "values": ["orders_*"]},
                ],
            },
            {
                "id": R2,
                "outcome": "unmanage",
                "conditions": [{"attribute": "table_name", "operator": "glob", "values": ["*_tmp"]}],
            },
        ],
    }

    assert DiscoveryPolicyContent.from_primitives(wire).to_primitives() == wire


def test_content_wire_form_refuses_an_unknown_key():
    """The wire form accepts only its own keys."""
    with pytest.raises(InvariantViolation):
        DiscoveryPolicyContent.from_primitives({"no_match_outcome": "unmanage", "rules": [], "priority": 1})
