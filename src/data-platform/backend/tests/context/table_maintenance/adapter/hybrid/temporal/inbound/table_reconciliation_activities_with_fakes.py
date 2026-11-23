"""Provide the table_reconciliation_activities_with_fakes test builder."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from context.table_maintenance.adapter.hybrid.temporal.inbound.activities import (
    TableReconciliationActivities,
)
from context.table_maintenance.application.service.table_maintenance_run import IssueTableMaintenanceRunIdsService
from context.table_maintenance.application.service.table_reconciliation import IssueTableReconciliationIdService
from tests.context.table_maintenance.adapter.hybrid.temporal.inbound.use_case_fakes import (
    FakeCreateRuns,
    FakePlan,
    FakeRecordReconciliation,
    FakeSkip,
)

if TYPE_CHECKING:
    from temporalio.client import Client

    from context.table_maintenance.application.port.inbound.table import (
        PlanTableMaintenanceUseCase,
    )
    from context.table_maintenance.application.port.inbound.table_maintenance_run import (
        CreateTableMaintenanceRunsUseCase,
        SkipTableMaintenanceRunUseCase,
    )
    from context.table_maintenance.application.port.inbound.table_reconciliation import (
        RecordTableReconciliationUseCase,
    )


def table_reconciliation_activities_with_fakes(
    *,
    plan: PlanTableMaintenanceUseCase | None = None,
    record: RecordTableReconciliationUseCase | None = None,
    create_runs: CreateTableMaintenanceRunsUseCase | None = None,
    skip: SkipTableMaintenanceRunUseCase | None = None,
    client: Client | None = None,
    attempt_deadline_seconds: int = 21600,
    max_attempts: int = 3,
    queue_wait_limit_seconds: int = 86400,
) -> TableReconciliationActivities:
    """Build the reconciliation activities with the real id services and a fake for each other use case not given."""
    return TableReconciliationActivities(
        plan=plan or FakePlan(),
        record=record or FakeRecordReconciliation(),
        create_runs=create_runs or FakeCreateRuns(),
        skip=skip or FakeSkip(),
        issue_reconciliation_id=IssueTableReconciliationIdService(),
        issue_run_ids=IssueTableMaintenanceRunIdsService(),
        client=client or MagicMock(),
        attempt_deadline_seconds=attempt_deadline_seconds,
        max_attempts=max_attempts,
        queue_wait_limit_seconds=queue_wait_limit_seconds,
    )
