"""Test that each activity calls its use case with the right input."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from temporalio.exceptions import ApplicationError

from adapter.inbound.temporal.activities import (
    DiscoveryActivities,
    MaintenanceActivities,
    ReconcileActivities,
)
from application.exceptions import NotFoundError
from application.port.inbound.reconcile.submit_maintenance_operation import (
    SubmitMaintenanceOperationUseCaseInputFilterItem,
)
from tests.adapter.inbound.temporal.use_case_fakes import (
    CREATED_AT,
    FakeCreateRun,
    FakeDelete,
    FakePlan,
    FakeRecordResult,
    FakeStatus,
    FakeSubmit,
    FakeSync,
)

NOW = "2026-10-24T01:02:03+00:00"
NOW_DT = datetime(2026, 10, 24, 1, 2, 3, tzinfo=UTC)


def _reconcile(submit: FakeSubmit | None = None) -> tuple[ReconcileActivities, dict]:
    fakes = {
        "plan": FakePlan(),
        "submit": submit or FakeSubmit(),
        "status": FakeStatus(),
        "delete": FakeDelete(),
    }
    activities = ReconcileActivities(
        plan=fakes["plan"],
        submit=fakes["submit"],
        status=fakes["status"],
        delete=fakes["delete"],
        callback_base_url="http://cp:8000",
    )
    return activities, fakes


def test_plan_passes_table_now_and_manual_operations_and_returns_dict():
    activities, fakes = _reconcile()
    result = activities.plan_table_maintenance(
        {"table_uuid": "u1", "now": NOW, "manual_operations": ["expire_snapshots"]}
    )
    request = fakes["plan"].requests[0]
    assert request.table_uuid == "u1"
    assert request.now == NOW_DT
    assert request.manual_operations == ["expire_snapshots"]
    assert result == {
        "status": "planned",
        "reason": None,
        "reconcile_interval_seconds": 3600,
        "operations": [
            {
                "operation": "rewrite_data_files",
                "filters": [{"spec_id": 0, "where": "x = 1"}],
                "procedure_args": {"strategy": "binpack"},
            }
        ],
    }


def test_plan_without_manual_operations_defaults_to_none():
    activities, fakes = _reconcile()
    activities.plan_table_maintenance({"table_uuid": "u1", "now": NOW})
    assert fakes["plan"].requests[0].manual_operations is None


def test_submit_injects_callback_base_url_and_converts_filters():
    activities, fakes = _reconcile()
    result = activities.submit_maintenance_operation(
        {
            "run_id": "r1",
            "operation": "rewrite_data_files",
            "attempt": 2,
            "filters": [{"spec_id": 1, "where": "y = 2"}],
            "procedure_args": {"a": 1},
            "now": NOW,
        }
    )
    request = fakes["submit"].requests[0]
    assert request.run_id == "r1"
    assert request.operation == "rewrite_data_files"
    assert request.attempt == 2
    assert request.filters == [
        SubmitMaintenanceOperationUseCaseInputFilterItem(1, "y = 2")
    ]
    assert request.procedure_args == {"a": 1}
    assert request.callback_base_url == "http://cp:8000"
    assert request.now == NOW_DT
    assert result == {"app_name": "app-1"}


def test_submit_translates_not_found_to_non_retryable():
    activities, _ = _reconcile(FakeSubmit(NotFoundError("no run")))
    with pytest.raises(ApplicationError) as caught:
        activities.submit_maintenance_operation(
            {
                "run_id": "r1",
                "operation": "rewrite_data_files",
                "attempt": 1,
                "filters": [],
                "procedure_args": {},
                "now": NOW,
            }
        )
    assert caught.value.non_retryable
    assert caught.value.type == "NotFoundError"


def test_submit_keeps_other_errors_retryable():
    activities, _ = _reconcile(FakeSubmit(RuntimeError("k8s down")))
    with pytest.raises(RuntimeError, match="k8s down"):
        activities.submit_maintenance_operation(
            {
                "run_id": "r1",
                "operation": "rewrite_data_files",
                "attempt": 1,
                "filters": [],
                "procedure_args": {},
                "now": NOW,
            }
        )


def test_status_and_delete_pass_app_name():
    activities, fakes = _reconcile()
    assert activities.get_maintenance_job_status({"app_name": "app-9"}) == {
        "state": "FAILED",
        "error": "oom",
    }
    assert activities.delete_maintenance_job({"app_name": "app-9"}) == {
        "app_name": "app-9"
    }
    assert fakes["status"].requests[0].app_name == "app-9"
    assert fakes["delete"].requests[0].app_name == "app-9"


def test_create_run_passes_fields_and_returns_iso_dict():
    create, record = FakeCreateRun(), FakeRecordResult()
    activities = MaintenanceActivities(create_run=create, record_result=record)
    result = activities.create_maintenance_run(
        {
            "run_id": "r1",
            "table_uuid": "u1",
            "trigger": "scheduled",
            "operations": ["rewrite_data_files", "expire_snapshots"],
            "now": NOW,
        }
    )
    request = create.requests[0]
    assert request.run_id == "r1"
    assert request.table_uuid == "u1"
    assert request.trigger == "scheduled"
    assert request.operations == ["rewrite_data_files", "expire_snapshots"]
    assert request.now == NOW_DT
    assert result["run_id"] == "r1"
    assert result["status"] == "running"
    assert result["created_at"] == CREATED_AT.isoformat()


def test_record_result_passes_fields():
    create, record = FakeCreateRun(), FakeRecordResult()
    activities = MaintenanceActivities(create_run=create, record_result=record)
    result = activities.record_maintenance_operation_result(
        {
            "run_id": "r1",
            "operation": "expire_snapshots",
            "attempt": 3,
            "succeeded": False,
            "metrics": {},
            "error": "spark job failed",
            "now": NOW,
        }
    )
    request = record.requests[0]
    assert (request.run_id, request.operation, request.attempt) == (
        "r1",
        "expire_snapshots",
        3,
    )
    assert request.succeeded is False
    assert request.metrics == {}
    assert request.error == "spark job failed"
    assert request.now == NOW_DT
    assert result == {"run_id": "r1", "status": "running"}


def test_sync_passes_catalog_and_namespace():
    sync = FakeSync()
    activities = DiscoveryActivities(sync=sync)
    result = activities.sync_discovered_tables({"catalog": "iceberg", "namespace": "s"})
    assert sync.requests[0].catalog == "iceberg"
    assert sync.requests[0].namespace == "s"
    assert result == {"registered": 1, "renamed": 2, "dropped": 3, "skipped": 4}
    activities.sync_discovered_tables({"catalog": "iceberg"})
    assert sync.requests[1].namespace is None
