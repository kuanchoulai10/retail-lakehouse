"""Test decide_table_discovery: a table is decided by the policy of its nearest attachment."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.table import TableName
from context.table_maintenance.application.domain.model.table_discovery_policy import (
    DecidedBy,
    ManagementDecision,
)
from context.table_maintenance.application.domain.service.table_discovery_policy_attachment import (
    decide_table_discovery,
)
from tests.context.table_maintenance.application.domain.service.table_discovery_policy_attachment.discovery_policy_samples import (  # noqa: E501
    MANAGE_ALL,
    POLICIES,
    UNMANAGE_ALL,
    attached,
    catalog_target,
    namespace_target,
    table_target,
)

ORDERS = TableName(catalog="iceberg", namespace="sales.eu", table="orders")


def _decided_by(decision: ManagementDecision):
    assert decision.decided_by is not None
    return decision.decided_by


def test_the_table_attachment_beats_a_managing_catalog():
    """An excluding policy attached to a table opts it out of the catalog's managing policy."""
    decision = decide_table_discovery(
        ORDERS,
        "u1",
        [attached(catalog_target("iceberg"), MANAGE_ALL), attached(table_target(ORDERS, "u1"), UNMANAGE_ALL)],
        POLICIES,
    )

    assert (decision.manage, _decided_by(decision).policy_id) == (False, UNMANAGE_ALL.id)


def test_the_deepest_namespace_wins():
    """``sales.eu`` is nearer to ``sales.eu.orders`` than ``sales``, so its policy decides."""
    decision = decide_table_discovery(
        ORDERS,
        "u1",
        [
            attached(namespace_target("iceberg", "sales"), MANAGE_ALL),
            attached(namespace_target("iceberg", "sales.eu"), UNMANAGE_ALL),
        ],
        POLICIES,
    )

    assert (decision.manage, _decided_by(decision).policy_id) == (False, UNMANAGE_ALL.id)


def test_the_catalog_decides_when_nothing_nearer_is_attached():
    """With only the catalog attached, its policy decides, naming the position of the rule that matched."""
    decision = decide_table_discovery(ORDERS, "u1", [attached(catalog_target("iceberg"), MANAGE_ALL)], POLICIES)

    assert decision == ManagementDecision(
        manage=True, decided_by=DecidedBy(policy_id=MANAGE_ALL.id, policy_version=1, rule_position=1)
    )


def test_nothing_attached_decides_nothing():
    """With no attachment on the walk, nothing decides: the table is not managed and no policy is named."""
    assert decide_table_discovery(ORDERS, "u1", [], {}) == ManagementDecision.nothing_attached()


def test_attachments_off_the_walk_are_ignored():
    """An attachment on another catalog or another namespace never decides the table."""
    decision = decide_table_discovery(
        ORDERS,
        "u1",
        [attached(catalog_target("other"), MANAGE_ALL), attached(namespace_target("iceberg", "hr"), MANAGE_ALL)],
        POLICIES,
    )

    assert decision == ManagementDecision.nothing_attached()


def test_a_table_is_found_by_uuid_not_by_path():
    """A table attachment made under an old name still decides the table with the same uuid."""
    old_name = TableName(catalog="iceberg", namespace="staging", table="orders_old")
    decision = decide_table_discovery(
        ORDERS,
        "u1",
        [attached(catalog_target("iceberg"), UNMANAGE_ALL), attached(table_target(old_name, "u1"), MANAGE_ALL)],
        POLICIES,
    )

    assert (decision.manage, _decided_by(decision).policy_id) == (True, MANAGE_ALL.id)


def test_another_tables_attachment_never_decides():
    """A table attachment with the same path but another uuid is another table's."""
    decision = decide_table_discovery(ORDERS, "u1", [attached(table_target(ORDERS, "u2"), MANAGE_ALL)], POLICIES)

    assert decision == ManagementDecision.nothing_attached()


def test_an_attachment_without_its_policy_is_skipped():
    """The namespace's policy is gone (a race with its delete), so the catalog's policy decides."""
    decision = decide_table_discovery(
        ORDERS,
        "u1",
        [
            attached(catalog_target("iceberg"), MANAGE_ALL),
            attached(namespace_target("iceberg", "sales.eu"), UNMANAGE_ALL),
        ],
        {MANAGE_ALL.id: MANAGE_ALL},
    )

    assert (decision.manage, _decided_by(decision).policy_id) == (True, MANAGE_ALL.id)
