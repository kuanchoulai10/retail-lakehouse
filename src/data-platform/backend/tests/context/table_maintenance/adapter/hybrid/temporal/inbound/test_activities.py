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
    SubmitMaintenanceOperationUseCaseInput,
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
from tests.context.table_maintenance.adapter.hybrid.temporal.inbound.table_maintenance_activities_with_fakes import (  # noqa: E501
    table_maintenance_activities_with_fakes,
)
from tests.context.table_maintenance.adapter.hybrid.temporal.inbound.table_reconciliation_activities_with_fakes import (  # noqa: E501
    table_reconciliation_activities_with_fakes,
)
from tests.context.table_maintenance.adapter.hybrid.temporal.inbound.use_case_fakes import (
    CREATED_AT,
    GOLD_POLICY_ID,
    FakeCreateRun,
    FakeDelete,
    FakePlan,
    FakeRecordReconciliation,
    FakeRecordResult,
    FakeReleaseCandidates,
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

RUN_1 = "mr-00000000000000000000000001"
RUN_9 = "mr-00000000000000000000000009"
REC_1 = "rc-00000000000000000000000001"
NIGHTLY_POLICY_ID = "mp-00000000000000000000000004"

NOW = "2026-10-24T01:02:03+00:00"
NOW_DT = datetime(2026, 10, 24, 1, 2, 3, tzinfo=UTC)


def _reconcile(
    attempt_deadline_seconds: int = 21600,
    max_attempts: int = 3,
) -> tuple[TableReconciliationActivities, dict]:
    fakes = {
        "plan": FakePlan(),
        "record": FakeRecordReconciliation(),
        "release": FakeReleaseCandidates(),
    }
    activities = table_reconciliation_activities_with_fakes(
        plan=fakes["plan"],
        record=fakes["record"],
        release=fakes["release"],
        attempt_deadline_seconds=attempt_deadline_seconds,
        max_attempts=max_attempts,
    )
    return activities, fakes


def _maintain(submit: FakeSubmit | None = None) -> tuple[TableMaintenanceActivities, dict]:
    fakes = {
        "submit": submit or FakeSubmit(),
        "status": FakeStatus(),
        "delete": FakeDelete(),
        "pods_gateway": ScriptedReadMaintenanceJobPodsGateway(),
    }
    activities = table_maintenance_activities_with_fakes(
        submit=fakes["submit"],
        status=fakes["status"],
        delete=fakes["delete"],
        pods=GetMaintenanceJobPodsService(fakes["pods_gateway"]),
        callback_base_url="http://cp:8000",
    )
    return activities, fakes


def test_plan_passes_table_now_and_manual_operations_and_returns_dict():
    """The plan activity passes the table, time and manual operations to the use case and returns a dict."""
    activities, fakes = _reconcile()
    result = activities.plan_table_maintenance(
        {"table_uuid": "u1", "now": NOW, "manual_operations": ["expire_snapshots"], "run_id": RUN_1}
    )
    request = fakes["plan"].requests[0]
    assert request.table_uuid == "u1"
    assert request.now == NOW_DT
    assert request.manual_operations == ("expire_snapshots",)
    assert request.run_id == RUN_1
    assert result == {
        "status": "planned",
        "reason": None,
        "reconcile_interval_seconds": 3600,
        "table_name": "iceberg.sales.orders",
        "operations": [
            {
                "operation": "rewrite_data_files",
                "filters": [{"spec_id": 0, "where": "x = 1"}],
                "procedure_args": {"strategy": "binpack"},
                "start_size": "S",
                "candidate_partitions": [],
                "filter_sets": [],
            }
        ],
        "dry_run": False,
        "table_found": True,
        "checks": [],
        "policy_id": GOLD_POLICY_ID,
        "policy_version": 3,
        "policy_target": {"type": "namespace", "path": ["iceberg", "sales"]},
        "next_check_at": None,
        "attempt_deadline_seconds": 21600,
        "max_attempts": 3,
    }


def test_plan_payload_carries_policy_id():
    """The plan crosses Temporal pointing at its policy by ``mp-`` id; the name is no longer in the payload."""
    activities, _ = _reconcile()
    result = activities.plan_table_maintenance({"table_uuid": "u1", "now": NOW, "run_id": RUN_1})
    assert result["policy_id"] == GOLD_POLICY_ID
    assert "policy_name" not in result


def _full_plan() -> PlanTableMaintenanceUseCaseOutput:
    """Return a plan that sets every field, nested ones included, with datetimes and sequences."""
    where = PlanTableMaintenanceUseCaseOutput.Filter(spec_id=1, where="region = 'eu'")
    other = PlanTableMaintenanceUseCaseOutput.Filter(spec_id=1, where="region = 'us'")
    return PlanTableMaintenanceUseCaseOutput(
        status="planned",
        reason=None,
        reconcile_interval_seconds=900,
        table_name="iceberg.sales.orders",
        operations=(
            PlanTableMaintenanceUseCaseOutput.Operation(
                operation="rewrite_data_files",
                filters=(where, other),
                procedure_args={"strategy": "binpack", "options": {"min-input-files": "5"}},
                start_size="M",
                candidate_partitions=(
                    PlanTableMaintenanceUseCaseOutput.CandidatePartition(spec_id=1, values=("eu", 2026)),
                    PlanTableMaintenanceUseCaseOutput.CandidatePartition(spec_id=1, values=("us", None)),
                ),
                filter_sets=((where, other), (where,)),
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
        policy_version=3,
        policy_target={"type": "namespace", "path": ["iceberg", "sales"]},
        next_check_at=datetime(2026, 10, 24, 1, 32, 3, tzinfo=UTC),
    )


def test_plan_payload_keeps_every_field_of_a_full_plan():
    """The plan activity returns the exact dict the reconciliation workflow reads: lists, nested dicts, ISO times."""
    plan = FakePlan(_full_plan())
    activities, _ = _reconcile()
    activities._plan = plan  # noqa: SLF001

    result = activities.plan_table_maintenance(
        {"table_uuid": "u1", "now": NOW, "manual_operations": None, "run_id": RUN_1}
    )

    assert result == {
        "status": "planned",
        "reason": None,
        "reconcile_interval_seconds": 900,
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
                "candidate_partitions": [
                    {"spec_id": 1, "values": ["eu", 2026]},
                    {"spec_id": 1, "values": ["us", None]},
                ],
                "filter_sets": [
                    [{"spec_id": 1, "where": "region = 'eu'"}, {"spec_id": 1, "where": "region = 'us'"}],
                    [{"spec_id": 1, "where": "region = 'eu'"}],
                ],
            },
            {
                "operation": "expire_snapshots",
                "filters": [],
                "procedure_args": {"older_than": "2026-10-17T01:02:03+00:00", "retain_last": 3},
                "start_size": "S",
                "candidate_partitions": [],
                "filter_sets": [],
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
        "policy_version": 3,
        "policy_target": {"type": "namespace", "path": ["iceberg", "sales"]},
        "next_check_at": "2026-10-24T01:32:03+00:00",
        "attempt_deadline_seconds": 21600,
        "max_attempts": 3,
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
        "run_id": RUN_1,
        "run_start_failed": False,
        "policy_id": plan["policy_id"],
        "policy_version": plan["policy_version"],
        "policy_target": plan["policy_target"],
    }
    return json.loads(json.dumps(payload))


def test_plan_checks_come_back_into_the_record_input_unchanged():
    """The plan's checks cross Temporal as lists of dicts; the record input reads them back as the plan wrote them."""
    activities, fakes = _reconcile()
    activities._plan = FakePlan(_full_plan())  # noqa: SLF001
    plan = activities.plan_table_maintenance({"table_uuid": "u1", "now": NOW, "run_id": RUN_1})
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
        reconcile_interval_seconds=900,
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
        policy_version=3,
        policy_target={"type": "namespace", "path": ["iceberg", "sales"]},
    )


def test_plan_checks_are_recorded_as_the_measurements_the_plan_took():
    """A plan's checks, through Temporal and the record activity, list back as the reconciliation's measurements."""
    activities, _ = _reconcile()
    activities._plan = FakePlan(_measured_plan())  # noqa: SLF001
    repo = InMemoryTableReconciliationsRepo()
    activities._record = RecordTableReconciliationService(repo)  # noqa: SLF001
    plan = activities.plan_table_maintenance({"table_uuid": "u1", "now": NOW, "run_id": RUN_1})

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
    "run_id": RUN_1,
}


def test_plan_input_is_built_from_the_payload_the_reconciliation_workflow_sends():
    """The plan input reads the workflow's payload as sent: an ISO time and a list of operations."""
    built = PlanTableMaintenanceUseCaseInput.from_primitives(WORKFLOW_PLAN_REQUEST)

    assert built == PlanTableMaintenanceUseCaseInput(
        table_uuid="u1",
        now=NOW_DT,
        manual_operations=("expire_snapshots", "rewrite_manifests"),
        run_id=RUN_1,
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


def test_plan_input_takes_a_scheduled_payload_without_operations_or_run():
    """A scheduled plan's payload names no manual operations and may name no run."""
    built = PlanTableMaintenanceUseCaseInput.from_primitives(
        {"table_uuid": "u1", "now": NOW, "manual_operations": None, "run_id": None}
    )

    assert (built.manual_operations, built.run_id) == (None, None)


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


def test_plan_without_manual_operations_defaults_to_none():
    """The plan activity passes no manual operations and no run when the request names none."""
    activities, fakes = _reconcile()
    activities.plan_table_maintenance({"table_uuid": "u1", "now": NOW})
    assert fakes["plan"].requests[0].manual_operations is None
    assert fakes["plan"].requests[0].run_id is None


def test_release_compaction_candidates_passes_the_run_and_now():
    """The release activity hands back the candidates of a run that never started."""
    activities, fakes = _reconcile()

    result = activities.release_compaction_candidates({"run_id": RUN_1, "now": NOW})

    (request,) = fakes["release"].requests
    assert (request.run_id, request.now) == (RUN_1, NOW_DT)
    assert result == {"released": 2}


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
            "run_id": RUN_1,
            "run_start_failed": False,
            "policy_id": NIGHTLY_POLICY_ID,
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
            run_id=RUN_1,
            run_start_failed=False,
            policy_id=NIGHTLY_POLICY_ID,
            policy_version=4,
            policy_target={"type": "catalog", "path": ["prod"]},
        )
    ]
    assert result == {"recorded": True}


def test_submit_injects_callback_base_url_and_converts_filters():
    """The submit activity adds the callback base URL and converts its filter payload for the use case."""
    activities, fakes = _maintain()
    result = activities.submit_maintenance_operation(
        {
            "run_id": RUN_1,
            "operation": "rewrite_data_files",
            "attempt": 2,
            "filters": [{"spec_id": 1, "where": "y = 2"}],
            "procedure_args": {"a": 1},
            "now": NOW,
        }
    )
    request = fakes["submit"].requests[0]
    assert request.run_id == RUN_1
    assert request.operation == "rewrite_data_files"
    assert request.attempt == 2
    assert request.filters == (SubmitMaintenanceOperationUseCaseInput.Filter(spec_id=1, where="y = 2"),)
    assert request.procedure_args == {"a": 1}
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
            "filters": [],
            "procedure_args": {},
            "now": NOW,
            "size": "M",
        }
    )
    assert fakes["submit"].requests[0].size == "M"


def test_submit_activity_defaults_the_size_for_old_requests():
    """A submit request recorded before sizes existed runs at S."""
    activities, fakes = _maintain()
    activities.submit_maintenance_operation(
        {
            "run_id": RUN_1,
            "operation": "rewrite_data_files",
            "attempt": 1,
            "filters": [],
            "procedure_args": {},
            "now": NOW,
        }
    )
    assert fakes["submit"].requests[0].size == "S"


def test_submit_translates_not_found_to_non_retryable():
    """A not found error from submit becomes a non-retryable application error."""
    activities, _ = _maintain(FakeSubmit(NotFoundError("no run")))
    with pytest.raises(ApplicationError) as caught:
        activities.submit_maintenance_operation(
            {
                "run_id": RUN_1,
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
    """Other errors from submit propagate unchanged so Temporal retries them."""
    activities, _ = _maintain(FakeSubmit(RuntimeError("k8s down")))
    with pytest.raises(RuntimeError, match="k8s down"):
        activities.submit_maintenance_operation(
            {
                "run_id": RUN_1,
                "operation": "rewrite_data_files",
                "attempt": 1,
                "filters": [],
                "procedure_args": {},
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


def test_create_run_passes_fields_and_returns_iso_dict():
    """The create run activity passes its fields to the use case and returns ISO formatted timestamps."""
    create, record = FakeCreateRun(), FakeRecordResult()
    activities = table_maintenance_activities_with_fakes(create_run=create, record_result=record)
    result = activities.create_table_maintenance_run(
        {
            "run_id": RUN_1,
            "table_uuid": "u1",
            "trigger": "scheduled",
            "operations": ["rewrite_data_files", "expire_snapshots"],
            "execution_ref": "wf-r1",
            "now": NOW,
        }
    )
    request = create.requests[0]
    assert request.run_id == RUN_1
    assert request.execution_ref == "wf-r1"
    assert request.table_uuid == "u1"
    assert request.trigger == "scheduled"
    assert request.operations == ("rewrite_data_files", "expire_snapshots")
    assert request.now == NOW_DT
    assert result["run_id"] == RUN_1
    assert result["status"] == "running"
    assert result["created_at"] == CREATED_AT.isoformat()


def test_record_result_passes_fields():
    """The record result activity passes the run, attempt, outcome and metrics to the use case."""
    create, record = FakeCreateRun(), FakeRecordResult()
    activities = table_maintenance_activities_with_fakes(create_run=create, record_result=record)
    result = activities.record_table_maintenance_operation_result(
        {
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
    create, record = FakeCreateRun(), FakeRecordResult()
    activities = table_maintenance_activities_with_fakes(create_run=create, record_result=record)
    activities.record_table_maintenance_operation_result(
        {
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


def test_record_activity_defaults_keys_of_old_requests():
    """A record request from before failure classes reads as a reported result of a finished job, of three attempts."""
    create, record = FakeCreateRun(), FakeRecordResult()
    activities = table_maintenance_activities_with_fakes(create_run=create, record_result=record)
    activities.record_table_maintenance_operation_result(
        {
            "run_id": RUN_1,
            "operation": "rewrite_data_files",
            "attempt": 1,
            "succeeded": False,
            "metrics": {},
            "error": "boom",
            "now": NOW,
        }
    )
    request = record.requests[0]
    assert (request.ended_by, request.still_running, request.max_attempts) == ("result", False, 3)
    assert (request.policy_id, request.policy_version, request.policy_target) == (None, None, None)


def test_record_activity_passes_the_planned_policy():
    """The record activity passes the policy the run was planned under."""
    create, record = FakeCreateRun(), FakeRecordResult()
    activities = table_maintenance_activities_with_fakes(create_run=create, record_result=record)
    target = {"type": "namespace", "path": ["iceberg", "sales"]}
    activities.record_table_maintenance_operation_result(
        {
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
    }
    activities.sync_discovered_tables({"catalog": "iceberg"})
    assert sync.requests[1].namespace is None
