"""Test the table reconciliation routes."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation,
    Measurement,
    MeasurementComparison,
    MeasurementUnit,
    PolicyTarget,
    PolicyTargetType,
    TableId,
    TableMaintenancePolicyId,
    TableMaintenanceRunId,
    TableReconciliationId,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    MaintenancePolicyContent,
    TableMaintenancePolicy,
    TableMaintenancePolicyName,
)
from context.table_maintenance.application.domain.model.table_reconciliation import (
    OperationOutcome,
    OperationResult,
    ReconciliationOutcome,
    TableReconciliation,
    WakeReason,
)
from context.table_maintenance.application.service.table_reconciliation import (
    GetTableReconciliationService,
    ListTableReconciliationsService,
)
from tests.context.table_maintenance.adapter.inbound.web.web_test_support import build_client
from tests.context.table_maintenance.fakes.in_memory_table_maintenance_policies_repo import (
    InMemoryTableMaintenancePoliciesRepo,
)
from tests.context.table_maintenance.fakes.in_memory_table_reconciliations_repo import (
    InMemoryTableReconciliationsRepo,
)

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

NOW = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)
OLD = "rc-00000000000000000000000001"
NEW = "rc-00000000000000000000000002"
FIRST = "rc-00000000000000000000000003"
SECOND = "rc-00000000000000000000000004"
THIRD = "rc-00000000000000000000000005"
RUN_1 = "mr-00000000000000000000000001"
RUN_2 = "mr-00000000000000000000000002"
NIGHTLY = TableMaintenancePolicyId("mp-00000000000000000000000004")


def _reconciliation(
    rec_id: str, at: datetime, table: str = "t-1", operations: tuple[OperationOutcome, ...] | None = None
) -> TableReconciliation:
    return TableReconciliation.record(
        id=TableReconciliationId(rec_id),
        table_uuid=TableId(table),
        reconciled_at=at,
        wake_reasons={WakeReason.SCHEDULE: 1},
        dry_run=False,
        outcome=ReconciliationOutcome.PLANNED,
        skip_reason=None,
        operations=operations
        or [
            OperationOutcome(
                operation=MaintenanceOperation.REWRITE_DATA_FILES,
                result=OperationResult.NOT_NEEDED,
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
        policy_id=NIGHTLY,
        policy_name=TableMaintenancePolicyName(value="nightly"),
        policy_version=4,
        policy_target=PolicyTarget(type=PolicyTargetType.NAMESPACE, path=("prod", "sales")),
    )


def _client(*items: TableReconciliation) -> TestClient:
    repo = InMemoryTableReconciliationsRepo()
    for item in items:
        repo.create(item)
    policies = InMemoryTableMaintenancePoliciesRepo()
    policies.create(
        TableMaintenancePolicy(
            id=NIGHTLY,
            name=TableMaintenancePolicyName(value="nightly"),
            content=MaintenancePolicyContent.platform_default(),
            version=4,
            created_at=NOW,
            updated_at=NOW,
        )
    )
    return build_client(
        list_table_reconciliations=ListTableReconciliationsService(repo, policies),
        get_table_reconciliation=GetTableReconciliationService(repo, policies),
    )


def _ids(response) -> list[str]:  # noqa: ANN001
    return [r["reconciliation_id"] for r in response.json()]


def test_lists_newest_first() -> None:
    """The newest reconciliation comes first."""
    client = _client(_reconciliation(OLD, NOW - timedelta(hours=2)), _reconciliation(NEW, NOW))

    response = client.get("/v1/tables/t-1/reconciliations")

    assert response.status_code == 200
    assert _ids(response) == [NEW, OLD]


def test_before_pages_older_records() -> None:
    """Only records strictly before the cursor are returned."""
    client = _client(
        _reconciliation(FIRST, NOW - timedelta(hours=2)),
        _reconciliation(SECOND, NOW - timedelta(hours=1)),
        _reconciliation(THIRD, NOW),
    )

    response = client.get("/v1/tables/t-1/reconciliations", params={"before": (NOW - timedelta(hours=1)).isoformat()})

    assert _ids(response) == [FIRST]


def test_limit_caps_the_page() -> None:
    """The limit caps the number of records."""
    client = _client(_reconciliation(FIRST, NOW - timedelta(hours=1)), _reconciliation(SECOND, NOW))

    assert _ids(client.get("/v1/tables/t-1/reconciliations", params={"limit": 1})) == [SECOND]


def test_limit_above_200_is_422() -> None:
    """A limit above 200 is rejected."""
    assert _client().get("/v1/tables/t-1/reconciliations", params={"limit": 201}).status_code == 422


def test_limit_below_1_is_422() -> None:
    """A limit below 1 is rejected."""
    assert _client().get("/v1/tables/t-1/reconciliations", params={"limit": 0}).status_code == 422


def test_unknown_table_returns_empty_list() -> None:
    """A table with no records lists as empty."""
    response = _client(_reconciliation(FIRST, NOW)).get("/v1/tables/other/reconciliations")

    assert response.status_code == 200
    assert response.json() == []


def test_context_measurement_has_null_threshold_and_met() -> None:
    """A context measurement carries null threshold, comparison and met."""
    body = _client(_reconciliation(FIRST, NOW)).get("/v1/tables/t-1/reconciliations").json()[0]

    operation = body["operations"][0]
    assert operation["operation"] == "rewrite_data_files"
    assert operation["result"] == "not_needed"
    assert "combine" not in operation
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
    assert operation["run_id"] is None
    assert "run_id" not in body


def test_the_api_shows_the_run_on_each_operation() -> None:
    """A started operation shows the mr- id of its run; a record has no run id of its own."""
    started = tuple(
        OperationOutcome(
            operation=operation, result=OperationResult.STARTED, run_id=TableMaintenanceRunId(run), measurements=()
        )
        for operation, run in (
            (MaintenanceOperation.REWRITE_DATA_FILES, RUN_1),
            (MaintenanceOperation.EXPIRE_SNAPSHOTS, RUN_2),
        )
    )
    reconciliation = _reconciliation(FIRST, NOW, operations=started)

    body = _client(reconciliation).get("/v1/tables/t-1/reconciliations").json()[0]

    assert [(o["operation"], o["run_id"]) for o in body["operations"]] == [
        ("rewrite_data_files", RUN_1),
        ("expire_snapshots", RUN_2),
    ]
    assert "run_id" not in body


def test_response_names_the_policy_used() -> None:
    """Each record carries the policy's id, its current name, the version and the target."""
    body = _client(_reconciliation(FIRST, NOW)).get("/v1/tables/t-1/reconciliations").json()[0]

    assert body["policy_id"] == NIGHTLY.value
    assert body["policy_name"] == "nightly"
    assert body["policy_deleted"] is False
    assert body["policy_version"] == 4
    assert body["policy_target"] == {"type": "namespace", "path": ["prod", "sales"]}


def test_response_under_a_deleted_policy_keeps_its_name() -> None:
    """A record whose policy was deleted since keeps the policy id and the name it recorded, flagged deleted."""
    repo = InMemoryTableReconciliationsRepo()
    repo.create(_reconciliation(FIRST, NOW))
    client = build_client(
        list_table_reconciliations=ListTableReconciliationsService(repo, InMemoryTableMaintenancePoliciesRepo())
    )

    body = client.get("/v1/tables/t-1/reconciliations").json()[0]

    assert (body["policy_id"], body["policy_name"], body["policy_deleted"]) == (NIGHTLY.value, "nightly", True)


def test_the_route_reads_one_reconciliation() -> None:
    """One record reads by its id, with the body the listing gives for it."""
    client = _client(_reconciliation(OLD, NOW - timedelta(hours=2)), _reconciliation(NEW, NOW))

    response = client.get(f"/v1/table-reconciliations/{OLD}")

    assert response.status_code == 200
    assert response.json() == client.get("/v1/tables/t-1/reconciliations").json()[1]


def test_the_route_is_404_for_an_unknown_id() -> None:
    """An id nothing was recorded under is 404."""
    assert _client(_reconciliation(OLD, NOW)).get(f"/v1/table-reconciliations/{NEW}").status_code == 404


def test_the_route_is_422_for_a_malformed_id() -> None:
    """An id that is not an rc- id is 422."""
    assert _client().get("/v1/table-reconciliations/not-an-id").status_code == 422
