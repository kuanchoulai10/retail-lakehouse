"""Test the candidate_policy_targets domain service."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.table import TableName
from context.table_maintenance.application.domain.model.table_maintenance_policy_attachment import (
    PolicyTarget,
    PolicyTargetType,
)
from context.table_maintenance.application.domain.service.table_maintenance_policy_attachment import (
    candidate_policy_targets,
)


def test_candidates_run_from_table_to_catalog():
    """The table comes first, then each namespace prefix deepest first, then the catalog."""
    name = TableName(catalog="prod", namespace="sales.eu", table="orders")

    assert candidate_policy_targets(name, "u-1") == (
        PolicyTarget(type=PolicyTargetType.TABLE, path=("prod", "sales", "eu", "orders"), table_uuid="u-1"),
        PolicyTarget(type=PolicyTargetType.NAMESPACE, path=("prod", "sales", "eu")),
        PolicyTarget(type=PolicyTargetType.NAMESPACE, path=("prod", "sales")),
        PolicyTarget(type=PolicyTargetType.CATALOG, path=("prod",)),
    )
