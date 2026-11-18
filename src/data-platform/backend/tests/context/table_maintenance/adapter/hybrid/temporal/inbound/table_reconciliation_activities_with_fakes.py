"""Provide the table_reconciliation_activities_with_fakes test builder."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from context.table_maintenance.adapter.hybrid.temporal.inbound.activities import (
    TableReconciliationActivities,
)
from tests.context.table_maintenance.adapter.hybrid.temporal.inbound.use_case_fakes import (
    FakePlan,
    FakeRecordReconciliation,
    FakeReleaseCandidates,
)

if TYPE_CHECKING:
    from temporalio.client import Client

    from context.table_maintenance.application.port.inbound.compaction_candidate import (
        ReleaseCompactionCandidatesUseCase,
    )
    from context.table_maintenance.application.port.inbound.table import (
        PlanTableMaintenanceUseCase,
    )
    from context.table_maintenance.application.port.inbound.table_reconciliation import (
        RecordTableReconciliationUseCase,
    )


def table_reconciliation_activities_with_fakes(
    *,
    plan: PlanTableMaintenanceUseCase | None = None,
    record: RecordTableReconciliationUseCase | None = None,
    release: ReleaseCompactionCandidatesUseCase | None = None,
    client: Client | None = None,
    attempt_deadline_seconds: int = 21600,
    max_attempts: int = 3,
) -> TableReconciliationActivities:
    """Build the reconciliation activities, a recording fake for every use case and a mock client not given."""
    return TableReconciliationActivities(
        plan=plan or FakePlan(),
        record=record or FakeRecordReconciliation(),
        release=release or FakeReleaseCandidates(),
        client=client or MagicMock(),
        attempt_deadline_seconds=attempt_deadline_seconds,
        max_attempts=max_attempts,
    )
