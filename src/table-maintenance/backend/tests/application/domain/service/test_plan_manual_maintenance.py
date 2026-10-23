from __future__ import annotations

from application.domain.model.maintenance import MaintenanceOperation as Op
from application.domain.service.plan_manual_maintenance import plan_manual_maintenance


def test_manual_plan_runs_named_operations_whole_table():
    plan = plan_manual_maintenance(
        [Op.EXPIRE_SNAPSHOTS, Op.REWRITE_DATA_FILES, Op.EXPIRE_SNAPSHOTS]
    )
    assert [p.operation for p in plan.operations] == [
        Op.REWRITE_DATA_FILES,
        Op.EXPIRE_SNAPSHOTS,
    ]
    assert all(p.partitions == () for p in plan.operations)


def test_manual_plan_of_nothing_is_empty():
    assert plan_manual_maintenance([]).is_empty
