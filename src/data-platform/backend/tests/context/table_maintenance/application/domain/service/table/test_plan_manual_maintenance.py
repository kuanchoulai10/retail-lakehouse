"""Test the plan for manually requested maintenance operations."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation as Op,
)
from context.table_maintenance.application.domain.service.table import (
    plan_manual_maintenance,
)


def test_manual_plan_runs_named_operations_whole_table():
    """A manual plan runs the named operations in canonical order over the whole table."""
    plan = plan_manual_maintenance([Op.EXPIRE_SNAPSHOTS, Op.REWRITE_DATA_FILES, Op.EXPIRE_SNAPSHOTS])
    assert [p.operation for p in plan.operations] == [
        Op.REWRITE_DATA_FILES,
        Op.EXPIRE_SNAPSHOTS,
    ]
    assert all(p.partitions == () for p in plan.operations)


def test_manual_plan_of_nothing_is_empty():
    """A manual plan of no operations is empty."""
    assert plan_manual_maintenance([]).is_empty
