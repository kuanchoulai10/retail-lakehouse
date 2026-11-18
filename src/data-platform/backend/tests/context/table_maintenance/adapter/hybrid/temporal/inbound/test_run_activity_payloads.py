"""Pin the dicts the run, job and reconciliation activities return, exactly as the workflows read them."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from temporalio.exceptions import ApplicationError

from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance import (
    DEFAULT_MAX_ATTEMPTS,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound.activities import (
    TableMaintenanceActivities,
    TableReconciliationActivities,
)
from context.table_maintenance.application.port.inbound.compaction_candidate import (
    ReleaseCompactionCandidatesUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    CreateTableMaintenanceRunUseCaseInput,
    CreateTableMaintenanceRunUseCaseOutput,
    DeleteMaintenanceJobUseCaseInput,
    GetMaintenanceJobPodsUseCaseInput,
    GetMaintenanceJobStatusUseCaseInput,
    RecordTableMaintenanceOperationResultUseCaseInput,
    RecordTableMaintenanceOperationResultUseCaseOutput,
    SubmitMaintenanceOperationUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_reconciliation import (
    RecordTableReconciliationUseCaseInput,
)
from context.table_maintenance.application.service.table_maintenance_run import (
    GetMaintenanceJobPodsService,
)
from tests.context.table_maintenance.adapter.hybrid.temporal.inbound.use_case_fakes import (
    FakeCreateRun,
    FakeDelete,
    FakePlan,
    FakeRecordReconciliation,
    FakeRecordResult,
    FakeReleaseCandidates,
    FakeStatus,
    FakeSubmit,
)
from tests.context.table_maintenance.fakes.scripted_read_maintenance_job_pods_gateway import (
    ScriptedReadMaintenanceJobPodsGateway,
)

NOW = "2026-10-24T01:02:03+00:00"
STARTED = datetime(2026, 10, 24, 1, 5, tzinfo=UTC)
FAILED = datetime(2026, 10, 24, 1, 20, 30, tzinfo=UTC)
RETRIED = datetime(2026, 10, 24, 1, 22, tzinfo=UTC)

CREATE_REQUEST = {
    "run_id": "r1",
    "table_uuid": "u1",
    "execution_ref": "wf-r1",
    "trigger": "manual",
    "operations": ["rewrite_data_files", "expire_snapshots"],
    "now": NOW,
}


def _reconcile(
    record: FakeRecordReconciliation | None = None, submit: FakeSubmit | None = None
) -> TableReconciliationActivities:
    return TableReconciliationActivities(
        plan=FakePlan(),
        record=record or FakeRecordReconciliation(),
        release=FakeReleaseCandidates(),
        submit=submit or FakeSubmit(),
        status=FakeStatus(),
        delete=FakeDelete(),
        pods=GetMaintenanceJobPodsService(ScriptedReadMaintenanceJobPodsGateway()),
        callback_base_url="http://cp:8000",
        attempt_deadline_seconds=21600,
        max_attempts=3,
    )


def _full_run() -> CreateTableMaintenanceRunUseCaseOutput:
    """Return a run that sets every field: an operation with two attempts and one not started."""
    return CreateTableMaintenanceRunUseCaseOutput(
        run_id="r1",
        table_uuid="u1",
        execution_ref="wf-r1",
        trigger="manual",
        status="running",
        operations=(
            {
                "operation": "rewrite_data_files",
                "status": "running",
                "attempts": 2,
                "started_at": STARTED,
                "finished_at": None,
                "job_name": "app-2",
                "metrics": {"rewritten_data_files_count": 4},
                "error": None,
                "expected_files": 7,
                "attempt_history": [
                    {
                        "attempt": 1,
                        "size": "S",
                        "status": "failed",
                        "started_at": STARTED,
                        "finished_at": FAILED,
                        "failure_class": "oom",
                        "error": "java.lang.OutOfMemoryError",
                        "event_log_finished": True,
                        "next_step": "retry_larger",
                        "next_size": "M",
                    },
                    {
                        "attempt": 2,
                        "size": "M",
                        "status": "running",
                        "started_at": RETRIED,
                        "finished_at": None,
                        "failure_class": None,
                        "error": None,
                        "event_log_finished": None,
                        "next_step": None,
                        "next_size": None,
                    },
                ],
            },
            {
                "operation": "expire_snapshots",
                "status": "pending",
                "attempts": 0,
                "started_at": None,
                "finished_at": None,
                "job_name": None,
                "metrics": {},
                "error": None,
                "expected_files": None,
                "attempt_history": [],
            },
        ),
        created_at=datetime(2026, 10, 24, 1, 2, 3, tzinfo=UTC),
        finished_at=None,
    )


def test_create_run_payload_keeps_every_field_of_a_full_run():
    """The create run activity returns the run as primitives: lists, nested dicts and ISO times, None kept."""
    activities = TableMaintenanceActivities(create_run=FakeCreateRun(_full_run()), record_result=FakeRecordResult())

    result = activities.create_table_maintenance_run(dict(CREATE_REQUEST))

    assert result == {
        "run_id": "r1",
        "table_uuid": "u1",
        "execution_ref": "wf-r1",
        "trigger": "manual",
        "status": "running",
        "operations": [
            {
                "operation": "rewrite_data_files",
                "status": "running",
                "attempts": 2,
                "started_at": "2026-10-24T01:05:00+00:00",
                "finished_at": None,
                "job_name": "app-2",
                "metrics": {"rewritten_data_files_count": 4},
                "error": None,
                "expected_files": 7,
                "attempt_history": [
                    {
                        "attempt": 1,
                        "size": "S",
                        "status": "failed",
                        "started_at": "2026-10-24T01:05:00+00:00",
                        "finished_at": "2026-10-24T01:20:30+00:00",
                        "failure_class": "oom",
                        "error": "java.lang.OutOfMemoryError",
                        "event_log_finished": True,
                        "next_step": "retry_larger",
                        "next_size": "M",
                    },
                    {
                        "attempt": 2,
                        "size": "M",
                        "status": "running",
                        "started_at": "2026-10-24T01:22:00+00:00",
                        "finished_at": None,
                        "failure_class": None,
                        "error": None,
                        "event_log_finished": None,
                        "next_step": None,
                        "next_size": None,
                    },
                ],
            },
            {
                "operation": "expire_snapshots",
                "status": "pending",
                "attempts": 0,
                "started_at": None,
                "finished_at": None,
                "job_name": None,
                "metrics": {},
                "error": None,
                "expected_files": None,
                "attempt_history": [],
            },
        ],
        "created_at": "2026-10-24T01:02:03+00:00",
        "finished_at": None,
    }
    assert json.loads(json.dumps(result)) == result


def test_record_result_payload_carries_the_decision_the_workflow_reads():
    """The record result activity returns the failure class, next step and next size the workflow acts on."""
    reply = RecordTableMaintenanceOperationResultUseCaseOutput(
        run_id="r1", status="running", failure_class="oom", next_step="retry_larger", next_size="M"
    )
    activities = TableMaintenanceActivities(create_run=FakeCreateRun(), record_result=FakeRecordResult(reply))

    result = activities.record_table_maintenance_operation_result(
        {
            "run_id": "r1",
            "operation": "rewrite_data_files",
            "attempt": 1,
            "succeeded": False,
            "metrics": {},
            "error": "java.lang.OutOfMemoryError",
            "now": NOW,
        }
    )

    assert result == {
        "run_id": "r1",
        "status": "running",
        "failure_class": "oom",
        "next_step": "retry_larger",
        "next_size": "M",
    }


def test_pods_payload_is_an_empty_list_once_every_pod_is_gone():
    """The pods activity returns an empty list, which the workflow reads as the pods being gone."""
    activities = _reconcile()

    result = activities.get_maintenance_job_pods({"run_id": "r1", "operation": "rewrite_data_files", "attempt": 1})

    assert result == {"live_pods": []}


NOW_DT = datetime(2026, 10, 24, 1, 2, 3, tzinfo=UTC)

WORKFLOW_SUBMIT_REQUEST = {
    "run_id": "r1",
    "operation": "rewrite_data_files",
    "attempt": 2,
    "filters": [{"spec_id": 1, "where": "region = 'eu'"}, {"spec_id": 1, "where": "region = 'us'"}],
    "procedure_args": {"strategy": "binpack", "options": {"min-input-files": "5"}},
    "size": "M",
    "now": NOW,
}

WORKFLOW_ATTEMPT_REQUEST = {"run_id": "r1", "operation": "rewrite_data_files", "attempt": 2}

WORKFLOW_RECORD_RESULT_REQUEST = {
    "run_id": "r1",
    "operation": "rewrite_data_files",
    "attempt": 2,
    "succeeded": True,
    "metrics": {"completed_without_callback": 1},
    "error": None,
    "ended_by": "result",
    "still_running": False,
    "max_attempts": 5,
    "policy_name": "gold",
    "policy_version": 3,
    "policy_target": {"type": "table", "path": ["iceberg", "sales", "orders"], "table_uuid": "u1"},
    "now": NOW,
}

WORKFLOW_CHECKS = [
    {
        "operation": "rewrite_data_files",
        "verdict": "due",
        "measurements": [
            {
                "key": "small_files",
                "observed": 40,
                "unit": "count",
                "threshold": 10,
                "comparison": ">=",
                "met": True,
            }
        ],
        "next_eligible_at": None,
    },
    {
        "operation": "expire_snapshots",
        "verdict": "cooling_down",
        "measurements": [],
        "next_eligible_at": "2026-10-24T07:00:00+00:00",
    },
]

WORKFLOW_RECORD_RECONCILIATION_REQUEST = {
    "reconciliation_id": "rec-1",
    "reconciled_at": NOW,
    "wake_reasons": {"catalog_commit": 3},
    "table_uuid": "u1",
    "dry_run": False,
    "status": "planned",
    "skip_reason": None,
    "checks": WORKFLOW_CHECKS,
    "run_id": "run-1",
    "run_start_failed": False,
    "policy_name": "gold",
    "policy_version": 3,
    "policy_target": {"type": "namespace", "path": ["iceberg", "sales"]},
}


def test_create_run_input_is_built_from_the_payload_the_maintenance_workflow_sends():
    """The create run input reads the workflow's payload: an ISO time and a list of operations."""
    assert CreateTableMaintenanceRunUseCaseInput.from_primitives(
        CREATE_REQUEST
    ) == CreateTableMaintenanceRunUseCaseInput(
        run_id="r1",
        table_uuid="u1",
        execution_ref="wf-r1",
        trigger="manual",
        operations=("rewrite_data_files", "expire_snapshots"),
        now=NOW_DT,
    )


def test_create_run_activity_hands_the_use_case_the_input_built_from_the_payload():
    """The create run activity builds its input with from_primitives."""
    create = FakeCreateRun()
    activities = TableMaintenanceActivities(create_run=create, record_result=FakeRecordResult())

    activities.create_table_maintenance_run(dict(CREATE_REQUEST))

    assert create.requests == [CreateTableMaintenanceRunUseCaseInput.from_primitives(CREATE_REQUEST)]


def test_submit_input_is_built_from_the_payload_the_maintenance_workflow_sends():
    """The submit input reads the workflow's payload with the worker's callback base URL added."""
    built = SubmitMaintenanceOperationUseCaseInput.from_primitives(
        {**WORKFLOW_SUBMIT_REQUEST, "callback_base_url": "http://cp:8000"}
    )

    assert built == SubmitMaintenanceOperationUseCaseInput(
        run_id="r1",
        operation="rewrite_data_files",
        attempt=2,
        filters=(
            SubmitMaintenanceOperationUseCaseInput.Filter(spec_id=1, where="region = 'eu'"),
            SubmitMaintenanceOperationUseCaseInput.Filter(spec_id=1, where="region = 'us'"),
        ),
        procedure_args={"strategy": "binpack", "options": {"min-input-files": "5"}},
        callback_base_url="http://cp:8000",
        now=NOW_DT,
        size="M",
    )


def test_submit_activity_hands_the_use_case_the_input_built_from_the_payload():
    """The submit activity adds its callback base URL to the payload and builds the input with from_primitives."""
    submit = FakeSubmit()
    activities = _reconcile(submit=submit)

    activities.submit_maintenance_operation(dict(WORKFLOW_SUBMIT_REQUEST))

    assert submit.requests == [
        SubmitMaintenanceOperationUseCaseInput.from_primitives(
            {**WORKFLOW_SUBMIT_REQUEST, "callback_base_url": "http://cp:8000"}
        )
    ]


def test_submit_activity_keeps_its_own_callback_base_url():
    """The callback base URL is the worker's setting, whatever the payload says."""
    submit = FakeSubmit()
    activities = _reconcile(submit=submit)

    activities.submit_maintenance_operation({**WORKFLOW_SUBMIT_REQUEST, "callback_base_url": "http://elsewhere"})

    assert submit.requests[0].callback_base_url == "http://cp:8000"


def test_submit_activity_refuses_a_mistyped_payload_without_retry():
    """A submit payload whose attempt is not an integer fails the activity at once."""
    submit = FakeSubmit()
    activities = _reconcile(submit=submit)

    with pytest.raises(ApplicationError) as caught:
        activities.submit_maintenance_operation({**WORKFLOW_SUBMIT_REQUEST, "attempt": "2"})

    assert caught.value.non_retryable
    assert caught.value.type == "InvariantViolation"
    assert submit.requests == []


@pytest.mark.parametrize(
    ("activity", "fake", "input_type"),
    [
        ("get_maintenance_job_status", "status", GetMaintenanceJobStatusUseCaseInput),
        ("delete_maintenance_job", "delete", DeleteMaintenanceJobUseCaseInput),
    ],
)
def test_job_activities_hand_the_use_case_the_input_built_from_the_payload(activity, fake, input_type):
    """The status and delete activities build their inputs from the workflow's attempt triple."""
    status, delete = FakeStatus(), FakeDelete()
    activities = TableReconciliationActivities(
        plan=FakePlan(),
        record=FakeRecordReconciliation(),
        release=FakeReleaseCandidates(),
        submit=FakeSubmit(),
        status=status,
        delete=delete,
        pods=GetMaintenanceJobPodsService(ScriptedReadMaintenanceJobPodsGateway()),
        callback_base_url="http://cp:8000",
        attempt_deadline_seconds=21600,
        max_attempts=3,
    )

    getattr(activities, activity)(dict(WORKFLOW_ATTEMPT_REQUEST))

    assert {"status": status, "delete": delete}[fake].requests == [
        input_type(run_id="r1", operation="rewrite_data_files", attempt=2)
    ]
    assert input_type.from_primitives(WORKFLOW_ATTEMPT_REQUEST) == input_type(
        run_id="r1", operation="rewrite_data_files", attempt=2
    )


def test_pods_input_is_built_from_the_payload_the_maintenance_workflow_sends():
    """The pods input reads the workflow's attempt triple."""
    assert GetMaintenanceJobPodsUseCaseInput.from_primitives(
        WORKFLOW_ATTEMPT_REQUEST
    ) == GetMaintenanceJobPodsUseCaseInput(run_id="r1", operation="rewrite_data_files", attempt=2)


def test_pods_activity_refuses_a_payload_without_an_attempt_without_retry():
    """A pods payload missing its attempt fails the activity at once."""
    activities = _reconcile()

    with pytest.raises(ApplicationError) as caught:
        activities.get_maintenance_job_pods({"run_id": "r1", "operation": "rewrite_data_files"})

    assert caught.value.non_retryable
    assert caught.value.type == "InvariantViolation"


def test_record_result_input_is_built_from_the_payload_the_maintenance_workflow_sends():
    """The record result input reads every key the workflow sends, the planned policy included."""
    assert RecordTableMaintenanceOperationResultUseCaseInput.from_primitives(
        WORKFLOW_RECORD_RESULT_REQUEST
    ) == RecordTableMaintenanceOperationResultUseCaseInput(
        run_id="r1",
        operation="rewrite_data_files",
        attempt=2,
        succeeded=True,
        metrics={"completed_without_callback": 1},
        error=None,
        now=NOW_DT,
        ended_by="result",
        still_running=False,
        max_attempts=5,
        policy_name="gold",
        policy_version=3,
        policy_target={"type": "table", "path": ["iceberg", "sales", "orders"], "table_uuid": "u1"},
    )


def test_record_result_input_defaults_the_keys_an_older_workflow_does_not_send():
    """A record request from before failure classes and planned policies reads with the old defaults."""
    built = RecordTableMaintenanceOperationResultUseCaseInput.from_primitives(
        {
            "run_id": "r1",
            "operation": "rewrite_data_files",
            "attempt": 1,
            "succeeded": False,
            "metrics": {},
            "error": "boom",
            "now": NOW,
        }
    )

    assert (built.ended_by, built.still_running, built.max_attempts) == ("result", False, 3)
    assert (built.policy_name, built.policy_version, built.policy_target) == (None, None, None)


def test_record_result_input_defaults_max_attempts_to_the_workflow_default():
    """An older request without max_attempts gets the attempts a maintenance workflow defaults to."""
    built = RecordTableMaintenanceOperationResultUseCaseInput.from_primitives(
        {k: v for k, v in WORKFLOW_RECORD_RESULT_REQUEST.items() if k != "max_attempts"}
    )

    assert built.max_attempts == DEFAULT_MAX_ATTEMPTS


def test_record_result_activity_hands_the_use_case_the_input_built_from_the_payload():
    """The record result activity builds its input with from_primitives and ignores a key a newer workflow adds."""
    record = FakeRecordResult()
    activities = TableMaintenanceActivities(create_run=FakeCreateRun(), record_result=record)

    activities.record_table_maintenance_operation_result({**WORKFLOW_RECORD_RESULT_REQUEST, "evidence_hint": "pods"})

    assert record.requests == [
        RecordTableMaintenanceOperationResultUseCaseInput.from_primitives(WORKFLOW_RECORD_RESULT_REQUEST)
    ]


def test_record_reconciliation_input_is_built_from_the_payload_the_reconciliation_workflow_sends():
    """The record input reads the workflow's payload: the plan's checks stay dicts, with lists inside."""
    built = RecordTableReconciliationUseCaseInput.from_primitives(WORKFLOW_RECORD_RECONCILIATION_REQUEST)

    assert built == RecordTableReconciliationUseCaseInput(
        reconciliation_id="rec-1",
        table_uuid="u1",
        reconciled_at=NOW_DT,
        wake_reasons={"catalog_commit": 3},
        dry_run=False,
        status="planned",
        skip_reason=None,
        checks=tuple(WORKFLOW_CHECKS),
        run_id="run-1",
        run_start_failed=False,
        policy_name="gold",
        policy_version=3,
        policy_target={"type": "namespace", "path": ["iceberg", "sales"]},
    )


def test_record_reconciliation_activity_hands_the_use_case_the_input_built_from_the_payload():
    """The record reconciliation activity builds its input with from_primitives."""
    record = FakeRecordReconciliation()
    activities = _reconcile(record=record)

    activities.record_table_reconciliation(dict(WORKFLOW_RECORD_RECONCILIATION_REQUEST))

    assert record.requests == [
        RecordTableReconciliationUseCaseInput.from_primitives(WORKFLOW_RECORD_RECONCILIATION_REQUEST)
    ]


def test_release_input_is_built_from_the_payload_the_reconciliation_workflow_sends():
    """The release input reads the run and the ISO time the workflow sends."""
    assert ReleaseCompactionCandidatesUseCaseInput.from_primitives(
        {"run_id": "run-1", "now": NOW}
    ) == ReleaseCompactionCandidatesUseCaseInput(run_id="run-1", now=NOW_DT)
