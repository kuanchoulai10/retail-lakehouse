"""Test the ListTableReconciliationsService."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from context.table_maintenance.application.port.inbound.table_reconciliation import (
    ListTableReconciliationsUseCaseInput,
)
from context.table_maintenance.application.service.table_reconciliation import (
    ListTableReconciliationsService,
    RecordTableReconciliationService,
)
from tests.context.table_maintenance.application.service.table_reconciliation.test_record_table_reconciliation_service import (  # noqa: E501
    _input,
)
from tests.context.table_maintenance.fakes.in_memory_table_reconciliations_repo import (
    InMemoryTableReconciliationsRepo,
)

NOW = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)


def test_maps_a_recorded_reconciliation_to_plain_items() -> None:
    """Enums become strings, measurements carry met, run_id is a string."""
    repo = InMemoryTableReconciliationsRepo()
    RecordTableReconciliationService(repo).execute(_input())

    output = ListTableReconciliationsService(repo).execute(ListTableReconciliationsUseCaseInput(table_uuid="table-1"))

    (item,) = output.items
    assert (item.reconciliation_id, item.outcome, item.run_id) == ("rec-1", "planned", "run-1")
    assert item.wake_reasons == {"schedule": 1}
    operation = item.operations[0]
    assert (operation.operation, operation.result, operation.combine) == ("rewrite_data_files", "started", "all")
    assert [(m.key, m.met) for m in operation.measurements] == [("small_files", True), ("data_bytes", None)]


def test_before_and_limit_are_passed_to_the_repo() -> None:
    """The cursor and the page size reach the repository."""
    repo = InMemoryTableReconciliationsRepo()
    record = RecordTableReconciliationService(repo)
    record.execute(_input(reconciliation_id="a", reconciled_at=NOW - timedelta(hours=1), run_id="r-a"))
    record.execute(_input(reconciliation_id="b", reconciled_at=NOW, run_id="r-b"))

    output = ListTableReconciliationsService(repo).execute(
        ListTableReconciliationsUseCaseInput(table_uuid="table-1", before=NOW, limit=1)
    )

    assert [i.reconciliation_id for i in output.items] == ["a"]
