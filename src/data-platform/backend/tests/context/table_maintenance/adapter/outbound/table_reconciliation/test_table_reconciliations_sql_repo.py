"""Test the repositories of the TableReconciliation aggregate."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from context.table_maintenance.adapter.outbound.table_reconciliation.sql import (
    TableReconciliationsSqlRepo,
)
from context.table_maintenance.application.domain.model.shared import (
    ConditionCombine,
    Measurement,
    MeasurementComparison,
    MeasurementUnit,
)
from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation as Op,
)
from context.table_maintenance.application.domain.model.table import TableId
from context.table_maintenance.application.domain.model.table_maintenance_run import (
    TableMaintenanceRunId,
)
from context.table_maintenance.application.domain.model.table_reconciliation import (
    OperationOutcome,
    OperationResult,
    ReconciliationOutcome,
    TableReconciliation,
    TableReconciliationId,
    WakeReason,
)
from context.table_maintenance.application.exceptions import ConflictError
from tests.context.table_maintenance.fakes.in_memory_table_reconciliations_repo import (
    InMemoryTableReconciliationsRepo,
)

if TYPE_CHECKING:
    from sqlalchemy import Engine

    from context.table_maintenance.application.port.outbound.table_reconciliation import (
        TableReconciliationsRepo,
    )

NOW = datetime(2026, 11, 10, 12, tzinfo=UTC)


def _rec(rec_id: str, table: str = "u1", at: datetime = NOW) -> TableReconciliation:
    return TableReconciliation.record(
        id=TableReconciliationId(rec_id),
        table_uuid=TableId(table),
        reconciled_at=at,
        wake_reasons={WakeReason.SCHEDULE: 2, WakeReason.CATALOG_COMMIT: 1},
        dry_run=True,
        outcome=ReconciliationOutcome.PLANNED,
        skip_reason=None,
        operations=(),
        run_id=None,
    )


@pytest.fixture(params=["sql", "memory"])
def repo(request: pytest.FixtureRequest, engine: Engine) -> TableReconciliationsRepo:
    """Provide each repository implementation."""
    if request.param == "sql":
        return TableReconciliationsSqlRepo(engine)
    return InMemoryTableReconciliationsRepo()


def test_create_and_get_round_trip(repo: TableReconciliationsRepo):
    """A stored reconciliation loads back with measurements, wake reasons and run id."""
    rec = TableReconciliation.record(
        id=TableReconciliationId("r1"),
        table_uuid=TableId("u1"),
        reconciled_at=NOW,
        wake_reasons={WakeReason.SCHEDULE: 2, WakeReason.RESUMED: 1},
        dry_run=False,
        outcome=ReconciliationOutcome.PLANNED,
        skip_reason=None,
        operations=(
            OperationOutcome(
                operation=Op.REWRITE_DATA_FILES,
                result=OperationResult.STARTED,
                combine=ConditionCombine.ANY,
                measurements=(
                    Measurement(
                        key="small_files",
                        observed=30,
                        unit=MeasurementUnit.COUNT,
                        threshold=10,
                        comparison=MeasurementComparison.AT_LEAST,
                    ),
                    Measurement(key="total_bytes", observed=5000, unit=MeasurementUnit.BYTES),
                ),
            ),
            OperationOutcome(
                operation=Op.EXPIRE_SNAPSHOTS,
                result=OperationResult.COOLING_DOWN,
                combine=ConditionCombine.ALL,
                measurements=(
                    Measurement(
                        key="age",
                        observed=60,
                        unit=MeasurementUnit.SECONDS,
                        threshold=3600,
                        comparison=MeasurementComparison.AT_MOST,
                    ),
                ),
                next_eligible_at=NOW + timedelta(hours=1),
            ),
        ),
        run_id=TableMaintenanceRunId("run-1"),
    )
    repo.create(rec)
    loaded = repo.get(TableReconciliationId("r1"))
    assert loaded is not None
    assert loaded.model_dump() == rec.model_dump()
    assert loaded.table_uuid == rec.table_uuid
    assert loaded.reconciled_at == NOW
    assert loaded.wake_reasons == {WakeReason.SCHEDULE: 2, WakeReason.RESUMED: 1}
    assert loaded.dry_run is False
    assert loaded.outcome is ReconciliationOutcome.PLANNED
    assert loaded.skip_reason is None
    assert loaded.run_id == TableMaintenanceRunId("run-1")
    assert loaded.operations == rec.operations
    assert loaded.operations[0].measurements[1].threshold is None
    assert loaded.operations[0].measurements[1].met is None
    assert loaded.operations[1].next_eligible_at == NOW + timedelta(hours=1)


def test_skipped_round_trip(repo: TableReconciliationsRepo):
    """A skipped reconciliation keeps its skip reason."""
    rec = TableReconciliation.record(
        id=TableReconciliationId("s1"),
        table_uuid=TableId("u1"),
        reconciled_at=NOW,
        wake_reasons={WakeReason.PAUSED: 1},
        dry_run=False,
        outcome=ReconciliationOutcome.SKIPPED,
        skip_reason="paused",
        operations=(),
        run_id=None,
    )
    repo.create(rec)
    loaded = repo.get(TableReconciliationId("s1"))
    assert loaded is not None
    assert loaded.skip_reason == "paused"
    assert loaded.operations == ()


def test_get_unknown_returns_none(repo: TableReconciliationsRepo):
    """An unknown id yields None."""
    assert repo.get(TableReconciliationId("nope")) is None


def test_create_duplicate_id_conflicts(repo: TableReconciliationsRepo):
    """Creating the same id twice is a conflict."""
    repo.create(_rec("r1"))
    with pytest.raises(ConflictError):
        repo.create(_rec("r1"))


def test_list_by_table_newest_first_with_cursor(repo: TableReconciliationsRepo):
    """Pages run newest first and the cursor excludes the given instant."""
    for i in range(4):
        repo.create(_rec(f"r{i}", at=NOW + timedelta(minutes=i)))
    repo.create(_rec("other", table="u2", at=NOW + timedelta(minutes=10)))
    page = repo.list_by_table(TableId("u1"))
    assert [r.id.value for r in page] == ["r3", "r2", "r1", "r0"]
    older = repo.list_by_table(TableId("u1"), before=NOW + timedelta(minutes=2))
    assert [r.id.value for r in older] == ["r1", "r0"]


def test_list_by_table_respects_limit(repo: TableReconciliationsRepo):
    """The limit caps the page."""
    for i in range(5):
        repo.create(_rec(f"r{i}", at=NOW + timedelta(minutes=i)))
    assert [r.id.value for r in repo.list_by_table(TableId("u1"), limit=2)] == ["r4", "r3"]


def test_delete_older_than_only_touches_that_table(repo: TableReconciliationsRepo):
    """Retention removes old rows of one table and leaves others."""
    repo.create(_rec("old", at=NOW - timedelta(days=40)))
    repo.create(_rec("new", at=NOW))
    repo.create(_rec("other-old", table="u2", at=NOW - timedelta(days=40)))
    assert repo.delete_older_than(TableId("u1"), NOW - timedelta(days=30)) == 1
    assert repo.get(TableReconciliationId("old")) is None
    assert repo.get(TableReconciliationId("new")) is not None
    assert repo.get(TableReconciliationId("other-old")) is not None
