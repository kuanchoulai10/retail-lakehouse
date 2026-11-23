"""Test that each activity calls its use case with the right input."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from temporalio.exceptions import ApplicationError

from context.table_maintenance.adapter.hybrid.temporal.inbound.activities import (
    TableDiscoveryActivities,
    TableMaintenanceActivities,
    TableReconciliationActivities,
)
from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table import (
    PlanTableMaintenanceUseCaseInput,
    PlanTableMaintenanceUseCaseOutput,
    SyncDiscoveredTablesUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    SkipTableMaintenanceRunUseCaseInput,
    SkipTableMaintenanceRunUseCaseOutput,
)
from context.table_maintenance.application.port.inbound.table_reconciliation import (
    ListTableReconciliationsUseCaseInput,
    RecordTableReconciliationUseCaseInput,
)
from context.table_maintenance.application.service.table_maintenance_run import (
    GetMaintenanceJobPodsService,
)
from context.table_maintenance.application.service.table_reconciliation import (
    ListTableReconciliationsService,
    RecordTableReconciliationService,
)
from tests.context.table_maintenance.adapter.hybrid.temporal.inbound.runs_repo_with_one_run import (
    runs_repo_with_one_run,
)
from tests.context.table_maintenance.adapter.hybrid.temporal.inbound.table_maintenance_activities_with_fakes import (  # noqa: E501
    table_maintenance_activities_with_fakes,
)
from tests.context.table_maintenance.adapter.hybrid.temporal.inbound.table_reconciliation_activities_with_fakes import (  # noqa: E501
    table_reconciliation_activities_with_fakes,
)
from tests.context.table_maintenance.adapter.hybrid.temporal.inbound.use_case_fakes import (
    GOLD_POLICY_ID,
    FakeCreateRuns,
    FakeDelete,
    FakePlan,
    FakeRaisePriority,
    FakeRecordReconciliation,
    FakeRecordResult,
    FakeRecordRunning,
    FakeSkip,
    FakeStatus,
    FakeSubmit,
    FakeSync,
)
from tests.context.table_maintenance.fakes.in_memory_table_maintenance_policies_repo import (
    InMemoryTableMaintenancePoliciesRepo,
)
from tests.context.table_maintenance.fakes.in_memory_table_reconciliations_repo import (
    InMemoryTableReconciliationsRepo,
)
from tests.context.table_maintenance.fakes.scripted_read_maintenance_job_pods_gateway import (
    ScriptedReadMaintenanceJobPodsGateway,
)
from tests.context.table_maintenance.planned_record_fields import PLANNED_RECORD_FIELDS

RUN_1 = "mr-00000000000000000000000001"
RUN_9 = "mr-00000000000000000000000009"
REC_1 = "rc-00000000000000000000000001"
NIGHTLY_POLICY_ID = "mp-00000000000000000000000004"

NOW = "2026-10-24T01:02:03+00:00"
NOW_DT = datetime(2026, 10, 24, 1, 2, 3, tzinfo=UTC)


def _reconcile(
    attempt_deadline_seconds: int = 21600,
    max_attempts: int = 3,
    queue_wait_limit_seconds: int = 86400,
) -> tuple[TableReconciliationActivities, dict]:
    fakes = {
        "plan": FakePlan(),
        "record": FakeRecordReconciliation(),
    }
    activities = table_reconciliation_activities_with_fakes(
        plan=fakes["plan"],
        record=fakes["record"],
        attempt_deadline_seconds=attempt_deadline_seconds,
        max_attempts=max_attempts,
        queue_wait_limit_seconds=queue_wait_limit_seconds,
    )
    return activities, fakes


def _maintain(submit: FakeSubmit | None = None) -> tuple[TableMaintenanceActivities, dict]:
    fakes = {
        "submit": submit or FakeSubmit(),
        "status": FakeStatus(),
        "delete": FakeDelete(),
        "pods_gateway": ScriptedReadMaintenanceJobPodsGateway(),
        "record_running": FakeRecordRunning(),
        "raise_priority": FakeRaisePriority(),
    }
    activities = table_maintenance_activities_with_fakes(
        submit=fakes["submit"],
        status=fakes["status"],
        delete=fakes["delete"],
        pods=GetMaintenanceJobPodsService(runs_repo_with_one_run(RUN_1), fakes["pods_gateway"]),
        record_running=fakes["record_running"],
        raise_priority=fakes["raise_priority"],
        callback_base_url="http://cp:8000",
    )
    return activities, fakes


def test_plan_passes_table_now_and_manual_operations_and_returns_dict():
    """The plan activity passes the table, time and manual operations to the use case and returns a dict."""
    activities, fakes = _reconcile()
    result = activities.plan_table_maintenance(
        {"table_uuid": "u1", "now": NOW, "manual_operations": ["expire_snapshots"]}
    )
    request = fakes["plan"].requests[0]
    assert request.table_uuid == "u1"
    assert request.now == NOW_DT
    assert request.manual_operations == ("expire_snapshots",)
    assert result == {
        "status": "planned",
        "reason": None,
        "schedule_interval_seconds": 3600,
        "catalog_commit_debounce_seconds": 300,
        "table_name": "iceberg.sales.orders",
        "operations": [
            {
                "operation": "rewrite_data_files",
                "filters": [{"spec_id": 0, "where": "x = 1"}],
                "procedure_args": {"strategy": "binpack"},
                "start_size": "S",
            }
        ],
        "dry_run": False,
        "table_found": True,
        "checks": [],
        "policy_id": GOLD_POLICY_ID,
        "policy_name": "gold",
        "policy_version": 3,
        "policy_target": {"type": "namespace", "path": ["iceberg", "sales"]},
        "priority": "P3",
        "attempt_deadline_seconds": 21600,
        "max_attempts": 3,
        "queue_wait_limit_seconds": 86400,
    }


def test_plan_payload_carries_policy_id_and_a_display_name():
    """The plan crosses Temporal pointing at its policy by ``mp-`` id, with its name then for the records to keep."""
    activities, _ = _reconcile()
    result = activities.plan_table_maintenance({"table_uuid": "u1", "now": NOW})
    assert (result["policy_id"], result["policy_name"]) == (GOLD_POLICY_ID, "gold")


def _full_plan() -> PlanTableMaintenanceUseCaseOutput:
    """Return a plan that sets every field, nested ones included, with datetimes and sequences."""
    where = PlanTableMaintenanceUseCaseOutput.Filter(spec_id=1, where="region = 'eu'")
    other = PlanTableMaintenanceUseCaseOutput.Filter(spec_id=1, where="region = 'us'")
    return PlanTableMaintenanceUseCaseOutput(
        status="planned",
        reason=None,
        schedule_interval_seconds=900,
        catalog_commit_debounce_seconds=None,
        table_name="iceberg.sales.orders",
        operations=(
            PlanTableMaintenanceUseCaseOutput.Operation(
                operation="rewrite_data_files",
                filters=(where, other),
                procedure_args={"strategy": "binpack", "options": {"min-input-files": "5"}},
                start_size="M",
            ),
            PlanTableMaintenanceUseCaseOutput.Operation(
                operation="expire_snapshots",
                filters=(),
                procedure_args={"older_than": "2026-10-17T01:02:03+00:00", "retain_last": 3},
            ),
        ),
        dry_run=False,
        table_found=True,
        checks=(
            PlanTableMaintenanceUseCaseOutput.Check(
                operation="rewrite_data_files",
                verdict="due",
                measurements=(
                    PlanTableMaintenanceUseCaseOutput.Measurement(
                        key="small_files", observed=40, unit="files", threshold=10, comparison="gte", met=True
                    ),
                    PlanTableMaintenanceUseCaseOutput.Measurement(
                        key="data_bytes", observed=1024, unit="bytes", threshold=None, comparison=None, met=None
                    ),
                ),
                next_eligible_at=None,
            ),
            PlanTableMaintenanceUseCaseOutput.Check(
                operation="expire_snapshots",
                verdict="cooling_down",
                measurements=(),
                next_eligible_at=datetime(2026, 10, 24, 7, 0, tzinfo=UTC),
            ),
        ),
        policy_id=GOLD_POLICY_ID,
        policy_name="gold",
        policy_version=3,
        policy_target={"type": "namespace", "path": ["iceberg", "sales"]},
    )


def test_plan_payload_keeps_every_field_of_a_full_plan():
    """The plan activity returns the exact dict the reconciliation workflow reads: lists, nested dicts, ISO times."""
    plan = FakePlan(_full_plan())
    activities, _ = _reconcile()
    activities._plan = plan  # noqa: SLF001

    result = activities.plan_table_maintenance({"table_uuid": "u1", "now": NOW, "manual_operations": None})

    assert result == {
        "status": "planned",
        "reason": None,
        "schedule_interval_seconds": 900,
        "catalog_commit_debounce_seconds": None,
        "table_name": "iceberg.sales.orders",
        "operations": [
            {
                "operation": "rewrite_data_files",
                "filters": [
                    {"spec_id": 1, "where": "region = 'eu'"},
                    {"spec_id": 1, "where": "region = 'us'"},
                ],
                "procedure_args": {"strategy": "binpack", "options": {"min-input-files": "5"}},
                "start_size": "M",
            },
            {
                "operation": "expire_snapshots",
                "filters": [],
                "procedure_args": {"older_than": "2026-10-17T01:02:03+00:00", "retain_last": 3},
                "start_size": "S",
            },
        ],
        "dry_run": False,
        "table_found": True,
        "checks": [
            {
                "operation": "rewrite_data_files",
                "verdict": "due",
                "measurements": [
                    {
                        "key": "small_files",
                        "observed": 40,
                        "unit": "files",
                        "threshold": 10,
                        "comparison": "gte",
                        "met": True,
                    },
                    {
                        "key": "data_bytes",
                        "observed": 1024,
                        "unit": "bytes",
                        "threshold": None,
                        "comparison": None,
                        "met": None,
                    },
                ],
                "next_eligible_at": None,
            },
            {
                "operation": "expire_snapshots",
                "verdict": "cooling_down",
                "measurements": [],
                "next_eligible_at": "2026-10-24T07:00:00+00:00",
            },
        ],
        "policy_id": GOLD_POLICY_ID,
        "policy_name": "gold",
        "policy_version": 3,
        "policy_target": {"type": "namespace", "path": ["iceberg", "sales"]},
        "priority": "P3",
        "attempt_deadline_seconds": 21600,
        "max_attempts": 3,
        "queue_wait_limit_seconds": 86400,
    }
    assert json.loads(json.dumps(result)) == result


def _record_payload_of(plan: dict) -> dict:
    """Return the record payload the reconciliation workflow builds from a plan, after a Temporal JSON trip."""
    payload = {
        "reconciliation_id": REC_1,
        "reconciled_at": NOW,
        "wake_reasons": {"catalog_commit": 2},
        "table_uuid": "u1",
        "dry_run": plan["dry_run"],
        "status": plan["status"],
        "skip_reason": plan["reason"],
        "checks": plan["checks"],
        "run_ids": {"rewrite_data_files": RUN_1},
        "run_start_failed": False,
        "policy_id": plan["policy_id"],
        "policy_name": plan["policy_name"],
        "policy_version": plan["policy_version"],
        "policy_target": plan["policy_target"],
    }
    return json.loads(json.dumps(payload))


def test_plan_checks_come_back_into_the_record_input_unchanged():
    """The plan's checks cross Temporal as lists of dicts; the record input reads them back as the plan wrote them."""
    activities, fakes = _reconcile()
    activities._plan = FakePlan(_full_plan())  # noqa: SLF001
    plan = activities.plan_table_maintenance({"table_uuid": "u1", "now": NOW})
    payload = _record_payload_of(plan)

    activities.record_table_reconciliation(payload)

    (request,) = fakes["record"].requests
    assert request == RecordTableReconciliationUseCaseInput.from_primitives(payload)
    assert request.checks == (
        {
            "operation": "rewrite_data_files",
            "verdict": "due",
            "measurements": [
                {
                    "key": "small_files",
                    "observed": 40,
                    "unit": "files",
                    "threshold": 10,
                    "comparison": "gte",
                    "met": True,
                },
                {
                    "key": "data_bytes",
                    "observed": 1024,
                    "unit": "bytes",
                    "threshold": None,
                    "comparison": None,
                    "met": None,
                },
            ],
            "next_eligible_at": None,
        },
        {
            "operation": "expire_snapshots",
            "verdict": "cooling_down",
            "measurements": [],
            "next_eligible_at": "2026-10-24T07:00:00+00:00",
        },
    )
    assert (request.policy_id, request.policy_version, request.policy_target) == (
        GOLD_POLICY_ID,
        3,
        {"type": "namespace", "path": ["iceberg", "sales"]},
    )


def _measured_plan() -> PlanTableMaintenanceUseCaseOutput:
    """Return a plan whose checks hold measurements the domain accepts: a due compaction and a cooling expiry."""
    return PlanTableMaintenanceUseCaseOutput(
        status="planned",
        reason=None,
        schedule_interval_seconds=900,
        catalog_commit_debounce_seconds=None,
        table_name="iceberg.sales.orders",
        operations=(),
        checks=(
            PlanTableMaintenanceUseCaseOutput.Check(
                operation="rewrite_data_files",
                verdict="due",
                measurements=(
                    PlanTableMaintenanceUseCaseOutput.Measurement(
                        key="small_files", observed=40, unit="count", threshold=10, comparison=">=", met=True
                    ),
                    PlanTableMaintenanceUseCaseOutput.Measurement(
                        key="data_bytes", observed=1024, unit="bytes", threshold=None, comparison=None, met=None
                    ),
                ),
                next_eligible_at=None,
            ),
            PlanTableMaintenanceUseCaseOutput.Check(
                operation="expire_snapshots",
                verdict="cooling_down",
                measurements=(),
                next_eligible_at=datetime(2026, 10, 24, 7, 0, tzinfo=UTC),
            ),
        ),
        policy_id=GOLD_POLICY_ID,
        policy_name="gold",
        policy_version=3,
        policy_target={"type": "namespace", "path": ["iceberg", "sales"]},
    )


def test_plan_checks_are_recorded_as_the_measurements_the_plan_took():
    """A plan's checks, through Temporal and the record activity, list back as the reconciliation's measurements."""
    activities, _ = _reconcile()
    activities._plan = FakePlan(_measured_plan())  # noqa: SLF001
    repo = InMemoryTableReconciliationsRepo()
    activities._record = RecordTableReconciliationService(repo)  # noqa: SLF001
    plan = activities.plan_table_maintenance({"table_uuid": "u1", "now": NOW})

    assert activities.record_table_reconciliation(_record_payload_of(plan)) == {"recorded": True}

    (listed,) = (
        ListTableReconciliationsService(repo, InMemoryTableMaintenancePoliciesRepo())
        .execute(ListTableReconciliationsUseCaseInput(table_uuid="u1"))
        .items
    )
    assert [(op.operation, op.result, op.next_eligible_at) for op in listed.operations] == [
        ("rewrite_data_files", "started", None),
        ("expire_snapshots", "cooling_down", datetime(2026, 10, 24, 7, 0, tzinfo=UTC)),
    ]
    assert [(m.key, m.observed, m.threshold, m.comparison, m.met) for m in listed.operations[0].measurements] == [
        ("small_files", 40, 10, ">=", True),
        ("data_bytes", 1024, None, None, None),
    ]


WORKFLOW_PLAN_REQUEST = {
    "table_uuid": "u1",
    "now": NOW,
    "manual_operations": ["expire_snapshots", "rewrite_manifests"],
}


def test_plan_input_is_built_from_the_payload_the_reconciliation_workflow_sends():
    """The plan input reads the workflow's payload as sent: an ISO time and a list of operations."""
    built = PlanTableMaintenanceUseCaseInput.from_primitives(WORKFLOW_PLAN_REQUEST)

    assert built == PlanTableMaintenanceUseCaseInput(
        table_uuid="u1",
        now=NOW_DT,
        manual_operations=("expire_snapshots", "rewrite_manifests"),
    )


def test_plan_activity_hands_the_use_case_the_input_built_from_the_payload():
    """The plan activity builds the use case input from the workflow payload with from_primitives."""
    activities, fakes = _reconcile()

    activities.plan_table_maintenance(dict(WORKFLOW_PLAN_REQUEST))

    assert fakes["plan"].requests == [PlanTableMaintenanceUseCaseInput.from_primitives(WORKFLOW_PLAN_REQUEST)]


def test_plan_activity_ignores_a_key_a_newer_workflow_sends():
    """During a rolling deploy a newer workflow may send a key this worker does not know; the plan still runs."""
    activities, fakes = _reconcile()

    activities.plan_table_maintenance({**WORKFLOW_PLAN_REQUEST, "priority_hint": "high"})

    assert fakes["plan"].requests == [PlanTableMaintenanceUseCaseInput.from_primitives(WORKFLOW_PLAN_REQUEST)]


def test_plan_input_takes_a_scheduled_payload_without_operations():
    """A scheduled plan's payload names no manual operations."""
    built = PlanTableMaintenanceUseCaseInput.from_primitives(
        {"table_uuid": "u1", "now": NOW, "manual_operations": None}
    )

    assert built == PlanTableMaintenanceUseCaseInput(table_uuid="u1", now=NOW_DT)


def test_plan_activity_refuses_a_payload_it_cannot_build_without_retry():
    """A plan payload whose time is not an ISO string fails the activity at once."""
    activities, fakes = _reconcile()

    with pytest.raises(ApplicationError) as caught:
        activities.plan_table_maintenance({"table_uuid": "u1", "now": 5})

    assert caught.value.non_retryable
    assert caught.value.type == "InvariantViolation"
    assert fakes["plan"].requests == []


def test_plan_carries_the_attempt_deadline():
    """The plan tells the run how long each attempt may take, from the worker setting."""
    activities, _ = _reconcile(attempt_deadline_seconds=120)

    result = activities.plan_table_maintenance({"table_uuid": "u1", "now": NOW})

    assert result["attempt_deadline_seconds"] == 120


def test_plan_carries_the_max_attempts():
    """The plan tells the run how many attempts each operation gets, from the worker setting."""
    activities, _ = _reconcile(max_attempts=5)

    result = activities.plan_table_maintenance({"table_uuid": "u1", "now": NOW})

    assert result["max_attempts"] == 5


def test_plan_carries_the_queue_wait_limit():
    """The plan tells the run how long each attempt may wait in its queue, from the worker setting."""
    activities, _ = _reconcile(queue_wait_limit_seconds=600)

    result = activities.plan_table_maintenance({"table_uuid": "u1", "now": NOW})

    assert result["queue_wait_limit_seconds"] == 600


def test_plan_without_manual_operations_defaults_to_none():
    """The plan activity passes no manual operations when the request names none."""
    activities, fakes = _reconcile()
    activities.plan_table_maintenance({"table_uuid": "u1", "now": NOW})
    assert fakes["plan"].requests[0].manual_operations is None


def test_plan_passes_the_manual_priority_and_defaults_to_none():
    """The plan activity hands the use case the manual priority of its payload, None when it names none."""
    activities, fakes = _reconcile()
    activities.plan_table_maintenance({"table_uuid": "u1", "now": NOW, "manual_priority": "P0"})
    activities.plan_table_maintenance({"table_uuid": "u1", "now": NOW})
    assert [r.manual_priority for r in fakes["plan"].requests] == ["P0", None]


CHECK = {
    "operation": "rewrite_data_files",
    "verdict": "due",
    "measurements": [],
    "next_eligible_at": None,
}


def test_record_reconciliation_passes_every_field_and_returns_dict():
    """The record activity passes the reconciliation, its reasons, checks and run link to the use case."""
    activities, fakes = _reconcile()
    result = activities.record_table_reconciliation(
        {
            "reconciliation_id": REC_1,
            "table_uuid": "u1",
            "reconciled_at": NOW,
            "wake_reasons": {"catalog_commit": 3, "previous_run_finished": 1},
            "dry_run": False,
            "status": "planned",
            "skip_reason": None,
            "checks": [CHECK],
            "run_ids": {"rewrite_data_files": RUN_1},
            "run_start_failed": False,
            "policy_id": NIGHTLY_POLICY_ID,
            "policy_name": "nightly",
            "policy_version": 4,
            "policy_target": {"type": "catalog", "path": ["prod"]},
        }
    )
    assert fakes["record"].requests == [
        RecordTableReconciliationUseCaseInput(
            reconciliation_id=REC_1,
            table_uuid="u1",
            reconciled_at=NOW_DT,
            wake_reasons={"catalog_commit": 3, "previous_run_finished": 1},
            dry_run=False,
            status="planned",
            skip_reason=None,
            checks=(CHECK,),
            run_ids={"rewrite_data_files": RUN_1},
            run_start_failed=False,
            policy_id=NIGHTLY_POLICY_ID,
            policy_name="nightly",
            policy_version=4,
            policy_target={"type": "catalog", "path": ["prod"]},
        )
    ]
    assert result == {"recorded": True}


def test_submit_injects_callback_base_url():
    """The submit activity adds the callback base URL; the where clauses and arguments come from the run."""
    activities, fakes = _maintain()
    result = activities.submit_maintenance_operation(
        {
            "run_id": RUN_1,
            "operation": "rewrite_data_files",
            "attempt": 2,
            "size": "S",
            "now": NOW,
        }
    )
    request = fakes["submit"].requests[0]
    assert request.run_id == RUN_1
    assert request.operation == "rewrite_data_files"
    assert request.attempt == 2
    assert request.callback_base_url == "http://cp:8000"
    assert request.now == NOW_DT
    assert result == {"job_name": "app-1"}


def test_submit_activity_passes_the_size():
    """The submit activity passes the attempt's size to the use case."""
    activities, fakes = _maintain()
    activities.submit_maintenance_operation(
        {
            "run_id": RUN_1,
            "operation": "rewrite_data_files",
            "attempt": 2,
            "now": NOW,
            "size": "M",
        }
    )
    assert fakes["submit"].requests[0].size == "M"


def test_submit_input_requires_a_size():
    """A submit request names the size of its attempt, as the maintenance workflow always sends one."""
    activities, fakes = _maintain()
    with pytest.raises(ApplicationError) as caught:
        activities.submit_maintenance_operation(
            {
                "run_id": RUN_1,
                "operation": "rewrite_data_files",
                "attempt": 1,
                "now": NOW,
            }
        )
    assert caught.value.type == "InvariantViolation"
    assert "size" in str(caught.value)
    assert fakes["submit"].requests == []


def test_submit_translates_not_found_to_non_retryable():
    """A not found error from submit becomes a non-retryable application error."""
    activities, _ = _maintain(FakeSubmit(NotFoundError("no run")))
    with pytest.raises(ApplicationError) as caught:
        activities.submit_maintenance_operation(
            {
                "run_id": RUN_1,
                "operation": "rewrite_data_files",
                "attempt": 1,
                "size": "S",
                "now": NOW,
            }
        )
    assert caught.value.non_retryable
    assert caught.value.type == "NotFoundError"


def test_submit_keeps_other_errors_retryable():
    """Other errors from submit propagate unchanged so Temporal retries them."""
    activities, _ = _maintain(FakeSubmit(RuntimeError("k8s down")))
    with pytest.raises(RuntimeError, match="k8s down"):
        activities.submit_maintenance_operation(
            {
                "run_id": RUN_1,
                "operation": "rewrite_data_files",
                "attempt": 1,
                "size": "S",
                "now": NOW,
            }
        )


def test_status_passes_the_attempt_triple():
    """The status activity passes the run, operation and attempt to the use case and returns its state."""
    activities, fakes = _maintain()
    request = {"run_id": RUN_9, "operation": "expire_snapshots", "attempt": 3}
    assert activities.get_maintenance_job_status(request) == {
        "state": "FAILED",
        "error": "oom",
        "driver_started_at": None,
    }
    status_request = fakes["status"].requests[0]
    assert (
        status_request.run_id,
        status_request.operation,
        status_request.attempt,
    ) == (
        RUN_9,
        "expire_snapshots",
        3,
    )


def test_delete_passes_the_attempt_triple():
    """The delete activity passes the run, operation and attempt to the use case and returns them."""
    activities, fakes = _maintain()
    result = activities.delete_maintenance_job({"run_id": RUN_1, "operation": "expire_snapshots", "attempt": 2})
    request = fakes["delete"].requests[0]
    assert (request.run_id, request.operation, request.attempt) == (
        RUN_1,
        "expire_snapshots",
        2,
    )
    assert result == {
        "run_id": RUN_1,
        "operation": "expire_snapshots",
        "attempt": 2,
    }


def test_get_maintenance_job_pods_activity_returns_live_pod_names():
    """The pods activity passes the attempt triple through and returns the names of its live pods."""
    activities, fakes = _maintain()
    fakes["pods_gateway"].set_live_pods(RUN_1, "rewrite_data_files", 2, "driver", "exec-1")

    result = activities.get_maintenance_job_pods({"run_id": RUN_1, "operation": "rewrite_data_files", "attempt": 2})

    assert result == {"live_pods": ["driver", "exec-1"]}
    assert [(c.run_id, c.operation, c.attempt) for c in fakes["pods_gateway"].calls] == [
        (RUN_1, "rewrite_data_files", 2)
    ]


def test_create_runs_activity_hands_the_use_case_the_plans_runs_and_returns_their_ids():
    """The create runs activity builds its input from the payload, every run in order, and returns the run ids."""
    create = FakeCreateRuns()
    activities = table_reconciliation_activities_with_fakes(create_runs=create)
    result = activities.create_maintenance_runs(
        {
            "table_uuid": "u1",
            "execution_ref": "wf-r1",
            "trigger": "scheduled",
            "priority": "P1",
            "now": NOW,
            "runs": [
                {"run_id": RUN_1, "operation": "rewrite_data_files", "filters": [{"spec_id": 0, "where": "x"}]},
                {"run_id": RUN_9, "operation": "expire_snapshots", "procedure_args": {"retain_last": 3}},
            ],
        }
    )
    request = create.requests[0]
    assert (request.table_uuid, request.execution_ref, request.trigger, request.priority, request.now) == (
        "u1",
        "wf-r1",
        "scheduled",
        "P1",
        NOW_DT,
    )
    assert [(r.run_id, r.operation) for r in request.runs] == [
        (RUN_1, "rewrite_data_files"),
        (RUN_9, "expire_snapshots"),
    ]
    assert request.runs[0].filters[0].where == "x"
    assert request.runs[1].procedure_args == {"retain_last": 3}
    assert result == {"run_ids": [RUN_1, RUN_9]}


def test_create_runs_activity_refuses_a_payload_without_a_priority():
    """A create payload that names no priority is refused without retry and creates nothing."""
    create = FakeCreateRuns()
    activities = table_reconciliation_activities_with_fakes(create_runs=create)
    with pytest.raises(ApplicationError) as caught:
        activities.create_maintenance_runs(
            {
                "table_uuid": "u1",
                "execution_ref": "wf-r1",
                "trigger": "scheduled",
                "now": NOW,
                "runs": [{"run_id": RUN_1, "operation": "expire_snapshots"}],
            }
        )
    assert (caught.value.type, caught.value.non_retryable) == ("InvariantViolation", True)
    assert create.requests == []


def test_skip_runs_activity_skips_each_run_with_the_reason_and_time():
    """The reconciliation's skip activity skips every run it names, one request each, and returns each reply."""
    skip = FakeSkip()
    activities = table_reconciliation_activities_with_fakes(skip=skip)

    result = activities.skip_maintenance_runs({"run_ids": [RUN_1, RUN_9], "reason": "not started", "now": NOW})

    assert skip.requests == [
        SkipTableMaintenanceRunUseCaseInput(run_id=RUN_1, reason="not started", now=NOW_DT),
        SkipTableMaintenanceRunUseCaseInput(run_id=RUN_9, reason="not started", now=NOW_DT),
    ]
    assert result == {
        "runs": [
            {"run_id": RUN_1, "status": "skipped", "skipped": True},
            {"run_id": RUN_9, "status": "skipped", "skipped": True},
        ]
    }


def test_skip_runs_activity_refuses_an_unknown_run_without_retry():
    """A skip of a run that does not exist fails the reconciliation's skip activity at once, as not found."""
    activities = table_reconciliation_activities_with_fakes(skip=FakeSkip(error=NotFoundError("no run")))

    with pytest.raises(ApplicationError) as caught:
        activities.skip_maintenance_runs({"run_ids": [RUN_1], "reason": "not started", "now": NOW})

    assert caught.value.non_retryable
    assert caught.value.type == "NotFoundError"


def test_record_result_passes_fields():
    """The record result activity passes the run, attempt, outcome and metrics to the use case."""
    record = FakeRecordResult()
    activities = table_maintenance_activities_with_fakes(record_result=record)
    result = activities.record_table_maintenance_operation_result(
        {
            **PLANNED_RECORD_FIELDS,
            "run_id": RUN_1,
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
        RUN_1,
        "expire_snapshots",
        3,
    )
    assert request.succeeded is False
    assert request.metrics == {}
    assert request.error == "spark job failed"
    assert request.now == NOW_DT
    assert result == {"run_id": RUN_1, "status": "running", "failure_class": None, "next_step": None, "next_size": None}


def test_record_activity_passes_ending_and_attempt_limit():
    """The record activity passes what ended the attempt, whether its job may still run and the attempt limit."""
    record = FakeRecordResult()
    activities = table_maintenance_activities_with_fakes(record_result=record)
    activities.record_table_maintenance_operation_result(
        {
            **PLANNED_RECORD_FIELDS,
            "run_id": RUN_1,
            "operation": "rewrite_data_files",
            "attempt": 2,
            "succeeded": False,
            "metrics": {},
            "error": "spark job timed out",
            "now": NOW,
            "ended_by": "timed_out",
            "still_running": True,
            "max_attempts": 5,
        }
    )
    request = record.requests[0]
    assert (request.ended_by, request.still_running, request.max_attempts) == ("timed_out", True, 5)


def test_record_activity_passes_the_planned_policy():
    """The record activity passes the policy the run was planned under."""
    record = FakeRecordResult()
    activities = table_maintenance_activities_with_fakes(record_result=record)
    target = {"type": "namespace", "path": ["iceberg", "sales"]}
    activities.record_table_maintenance_operation_result(
        {
            **PLANNED_RECORD_FIELDS,
            "run_id": RUN_1,
            "operation": "rewrite_data_files",
            "attempt": 1,
            "succeeded": False,
            "metrics": {},
            "error": "boom",
            "now": NOW,
            "policy_id": NIGHTLY_POLICY_ID,
            "policy_version": 4,
            "policy_target": target,
        }
    )
    request = record.requests[0]
    assert (request.policy_id, request.policy_version, request.policy_target) == (NIGHTLY_POLICY_ID, 4, target)


def test_sync_input_is_built_from_the_payload_the_discovery_workflow_sends():
    """The sync input reads the discovery workflow's payload as sent, a namespace or none."""
    assert SyncDiscoveredTablesUseCaseInput.from_primitives(
        {"catalog": "iceberg", "namespace": "sales"}
    ) == SyncDiscoveredTablesUseCaseInput(catalog="iceberg", namespace="sales")
    assert SyncDiscoveredTablesUseCaseInput.from_primitives(
        {"catalog": "iceberg", "namespace": None}
    ) == SyncDiscoveredTablesUseCaseInput(catalog="iceberg")


def test_sync_activity_hands_the_use_case_the_input_built_from_the_payload():
    """The sync activity builds the use case input from the workflow payload with from_primitives."""
    sync = FakeSync()
    activities = TableDiscoveryActivities(sync=sync)

    activities.sync_discovered_tables({"catalog": "iceberg", "namespace": None})

    assert sync.requests == [
        SyncDiscoveredTablesUseCaseInput.from_primitives({"catalog": "iceberg", "namespace": None})
    ]


def test_sync_passes_catalog_and_namespace():
    """The sync activity passes the catalog and namespace and returns the sync counts."""
    sync = FakeSync()
    activities = TableDiscoveryActivities(sync=sync)
    result = activities.sync_discovered_tables({"catalog": "iceberg", "namespace": "s"})
    assert sync.requests[0].catalog == "iceberg"
    assert sync.requests[0].namespace == "s"
    assert result == {
        "registered": 1,
        "renamed": 2,
        "dropped": 3,
        "skipped": 4,
        "ensured": 0,
        "managed": 0,
        "unmanaged": 0,
        "failure": None,
    }
    activities.sync_discovered_tables({"catalog": "iceberg"})
    assert sync.requests[1].namespace is None


def test_record_maintenance_attempt_running_activity_passes_the_driver_start():
    """The record running activity builds its input from the payload and returns the recorded running time."""
    activities, fakes = _maintain()

    result = activities.record_maintenance_attempt_running(
        {
            "run_id": RUN_1,
            "operation": "rewrite_data_files",
            "attempt": 2,
            "started_running_at": "2026-10-24T01:00:00+00:00",
            "now": NOW,
        }
    )

    request = fakes["record_running"].requests[0]
    assert (request.run_id, request.operation, request.attempt) == (RUN_1, "rewrite_data_files", 2)
    assert request.started_running_at == datetime(2026, 10, 24, 1, 0, 0, tzinfo=UTC)
    assert request.now == NOW_DT
    assert result == {"status": "running", "started_running_at": "2026-10-24T01:00:00+00:00"}


def test_raise_table_maintenance_run_priority_activity_passes_the_priority():
    """The raise priority activity builds its input from the payload and returns the run's priority."""
    activities, fakes = _maintain()

    result = activities.raise_table_maintenance_run_priority({"run_id": RUN_1, "priority": "P1", "now": NOW})

    request = fakes["raise_priority"].requests[0]
    assert (request.run_id, request.priority, request.now) == (RUN_1, "P1", NOW_DT)
    assert result == {"priority": "P1", "raised": True}


def test_raise_table_maintenance_run_priority_activity_passes_no_priority():
    """A payload without a priority asks for the table's current priority."""
    activities, fakes = _maintain()

    activities.raise_table_maintenance_run_priority({"run_id": RUN_1, "priority": None, "now": NOW})

    assert fakes["raise_priority"].requests[0].priority is None


def test_skip_activity_passes_the_run_reason_and_time_and_returns_the_reply():
    """The skip activity builds its input from the payload and returns whether the run was skipped."""
    skip = FakeSkip()
    activities = table_maintenance_activities_with_fakes(skip=skip)

    result = activities.skip_table_maintenance_run({"run_id": RUN_1, "reason": "stopped", "now": NOW})

    assert skip.requests == [SkipTableMaintenanceRunUseCaseInput(run_id=RUN_1, reason="stopped", now=NOW_DT)]
    assert result == {"run_id": RUN_1, "status": "skipped", "skipped": True}


def test_skip_activity_returns_a_run_left_alone_as_not_skipped():
    """A run no longer pending comes back with its status and ``skipped`` false, and the activity does not fail."""
    reply = SkipTableMaintenanceRunUseCaseOutput(run_id=RUN_1, status="succeeded", skipped=False)
    activities = table_maintenance_activities_with_fakes(skip=FakeSkip(reply))

    result = activities.skip_table_maintenance_run({"run_id": RUN_1, "reason": "stopped", "now": NOW})

    assert result == {"run_id": RUN_1, "status": "succeeded", "skipped": False}


def test_skip_activity_refuses_an_unknown_run_without_retry():
    """A skip of a run that does not exist fails the activity at once, as not found."""
    activities = table_maintenance_activities_with_fakes(skip=FakeSkip(error=NotFoundError("no run")))

    with pytest.raises(ApplicationError) as caught:
        activities.skip_table_maintenance_run({"run_id": RUN_1, "reason": "stopped", "now": NOW})

    assert caught.value.non_retryable
    assert caught.value.type == "NotFoundError"
