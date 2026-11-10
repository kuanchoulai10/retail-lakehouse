"""Test the table reconciliation routes."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import (
    ConditionCombine,
    MaintenanceOperation,
    Measurement,
    MeasurementComparison,
    MeasurementUnit,
)
from context.table_maintenance.application.domain.model.table import TableId
from context.table_maintenance.application.domain.model.table_reconciliation import (
    OperationOutcome,
    OperationResult,
    ReconciliationOutcome,
    TableReconciliation,
    TableReconciliationId,
    WakeReason,
)
from context.table_maintenance.application.service.table_reconciliation import (
    ListTableReconciliationsService,
)
from tests.context.table_maintenance.adapter.inbound.web.web_test_support import build_client
from tests.context.table_maintenance.fakes.in_memory_table_reconciliations_repo import (
    InMemoryTableReconciliationsRepo,
)

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

NOW = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)


def _reconciliation(rec_id: str, at: datetime, table: str = "t-1") -> TableReconciliation:
    return TableReconciliation.record(
        id=TableReconciliationId(rec_id),
        table_uuid=TableId(table),
        reconciled_at=at,
        wake_reasons={WakeReason.SCHEDULE: 1},
        dry_run=False,
        outcome=ReconciliationOutcome.PLANNED,
        skip_reason=None,
        operations=[
            OperationOutcome(
                operation=MaintenanceOperation.REWRITE_DATA_FILES,
                result=OperationResult.NOT_NEEDED,
                combine=ConditionCombine.ALL,
                measurements=(
                    Measurement(
                        key="small_files",
                        observed=3,
                        unit=MeasurementUnit.COUNT,
                        threshold=10,
                        comparison=MeasurementComparison.AT_LEAST,
                    ),
                    Measurement(key="data_bytes", observed=5, unit=MeasurementUnit.BYTES),
                ),
            )
        ],
        run_id=None,
    )


def _client(*items: TableReconciliation) -> TestClient:
    repo = InMemoryTableReconciliationsRepo()
    for item in items:
        repo.create(item)
    return build_client(list_table_reconciliations=ListTableReconciliationsService(repo))


def _ids(response) -> list[str]:  # noqa: ANN001
    return [r["reconciliation_id"] for r in response.json()]


def test_lists_newest_first() -> None:
    """The newest reconciliation comes first."""
    client = _client(_reconciliation("old", NOW - timedelta(hours=2)), _reconciliation("new", NOW))

    response = client.get("/v1/tables/t-1/reconciliations")

    assert response.status_code == 200
    assert _ids(response) == ["new", "old"]


def test_before_pages_older_records() -> None:
    """Only records strictly before the cursor are returned."""
    client = _client(
        _reconciliation("a", NOW - timedelta(hours=2)),
        _reconciliation("b", NOW - timedelta(hours=1)),
        _reconciliation("c", NOW),
    )

    response = client.get("/v1/tables/t-1/reconciliations", params={"before": (NOW - timedelta(hours=1)).isoformat()})

    assert _ids(response) == ["a"]


def test_limit_caps_the_page() -> None:
    """The limit caps the number of records."""
    client = _client(_reconciliation("a", NOW - timedelta(hours=1)), _reconciliation("b", NOW))

    assert _ids(client.get("/v1/tables/t-1/reconciliations", params={"limit": 1})) == ["b"]


def test_limit_above_200_is_422() -> None:
    """A limit above 200 is rejected."""
    assert _client().get("/v1/tables/t-1/reconciliations", params={"limit": 201}).status_code == 422


def test_limit_below_1_is_422() -> None:
    """A limit below 1 is rejected."""
    assert _client().get("/v1/tables/t-1/reconciliations", params={"limit": 0}).status_code == 422


def test_unknown_table_returns_empty_list() -> None:
    """A table with no records lists as empty."""
    response = _client(_reconciliation("a", NOW)).get("/v1/tables/other/reconciliations")

    assert response.status_code == 200
    assert response.json() == []


def test_context_measurement_has_null_threshold_and_met() -> None:
    """A context measurement carries null threshold, comparison and met."""
    body = _client(_reconciliation("a", NOW)).get("/v1/tables/t-1/reconciliations").json()[0]

    operation = body["operations"][0]
    assert operation["operation"] == "rewrite_data_files"
    assert operation["result"] == "not_needed"
    assert operation["combine"] == "all"
    assert operation["next_eligible_at"] is None
    condition, context = operation["measurements"]
    assert (condition["threshold"], condition["comparison"], condition["met"]) == (10, ">=", False)
    assert context == {
        "key": "data_bytes",
        "observed": 5,
        "unit": "bytes",
        "threshold": None,
        "comparison": None,
        "met": None,
    }
    assert body["wake_reasons"] == {"schedule": 1}
    assert body["outcome"] == "planned"
    assert body["run_id"] is None
