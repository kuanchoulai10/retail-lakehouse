"""Provide the runs_repo_with_one_run test builder."""

from __future__ import annotations

from datetime import UTC, datetime

from context.table_maintenance.application.domain.model.shared import MaintenanceOperation
from context.table_maintenance.application.domain.model.table import TableId
from context.table_maintenance.application.domain.model.table_maintenance_run import (
    TableMaintenanceRun,
    TableMaintenanceRunId,
    TriggerType,
)
from tests.context.table_maintenance.fakes.in_memory_table_maintenance_runs_repo import (
    InMemoryTableMaintenanceRunsRepo,
)

STORED_RUN_ID = "mr-00000000000000000000000001"


def runs_repo_with_one_run(
    run_id: str = STORED_RUN_ID, operation: str = "rewrite_data_files"
) -> InMemoryTableMaintenanceRunsRepo:
    """Return a runs repo holding one pending run of ``operation`` under ``run_id``.

    The job services look the run up before they reach a job, so an activity test of them needs the run stored.
    """
    repo = InMemoryTableMaintenanceRunsRepo()
    repo.create(
        TableMaintenanceRun.create(
            TableMaintenanceRunId(run_id),
            TableId("u1"),
            TriggerType.SCHEDULED,
            MaintenanceOperation(operation),
            datetime(2026, 10, 24, tzinfo=UTC),
            execution_ref="wf-r1",
        )
    )
    return repo
