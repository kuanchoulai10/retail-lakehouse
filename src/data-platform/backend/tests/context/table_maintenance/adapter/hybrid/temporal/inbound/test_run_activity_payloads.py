"""Pin the dicts the run, job and reconciliation activities return, exactly as the workflows read them."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from temporalio.exceptions import ApplicationError

from base import InvariantViolation
from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    CreateTableMaintenanceRunsUseCaseInput,
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
    FakeRecordReconciliation,
    FakeRecordResult,
    FakeStatus,
    FakeSubmit,
)
from tests.context.table_maintenance.planned_record_fields import PLANNED_RECORD_FIELDS

RUN_1 = "mr-00000000000000000000000001"
REC_1 = "rc-00000000000000000000000001"

NOW = "2026-10-24T01:02:03+00:00"

CREATE_RUN = {
    "run_id": RUN_1,
    "operation": "rewrite_data_files",
    "filters": [{"spec_id": 0, "where": "(`region` = 'eu')"}],
    "procedure_args": {"strategy": "binpack", "options": {"min-input-files": "5"}},
}
CREATE_REQUEST = {
    "table_uuid": "u1",
    "execution_ref": "wf-r1",
    "trigger": "manual",
    "priority": "P1",
    "now": NOW,
    "runs": [CREATE_RUN],
}


def test_create_runs_payload_is_the_run_ids_the_workflow_reads():
    """The create runs activity returns the ids of the plan's runs, as a JSON list."""
    activities = table_reconciliation_activities_with_fakes()

    result = activities.create_maintenance_runs(dict(CREATE_REQUEST))

    assert result == {"run_ids": [RUN_1]}
    assert json.loads(json.dumps(result)) == result


def test_record_result_payload_carries_the_decision_the_workflow_reads():
    """The record result activity returns the failure class, next step and next size the workflow acts on."""
    reply = RecordTableMaintenanceOperationResultUseCaseOutput(
        run_id=RUN_1, status="running", failure_class="oom", next_step="retry_larger", next_size="M"
    )
    activities = table_maintenance_activities_with_fakes(record_result=FakeRecordResult(reply))

    result = activities.record_table_maintenance_operation_result(
        {
            "run_id": RUN_1,
            "operation": "rewrite_data_files",
            "attempt": 1,
            "succeeded": False,
            "metrics": {},
            "error": "java.lang.OutOfMemoryError",
            "now": NOW,
            **PLANNED_RECORD_FIELDS,
        }
    )

    assert result == {
        "run_id": RUN_1,
        "status": "running",
        "failure_class": "oom",
        "next_step": "retry_larger",
        "next_size": "M",
    }


def test_pods_payload_is_an_empty_list_once_every_pod_is_gone():
    """The pods activity returns an empty list, which the workflow reads as the pods being gone."""
    activities = table_maintenance_activities_with_fakes()

    result = activities.get_maintenance_job_pods({"run_id": RUN_1, "operation": "rewrite_data_files", "attempt": 1})

    assert result == {"live_pods": []}


NOW_DT = datetime(2026, 10, 24, 1, 2, 3, tzinfo=UTC)

WORKFLOW_SUBMIT_REQUEST = {
    "run_id": RUN_1,
    "operation": "rewrite_data_files",
    "attempt": 2,
    "size": "M",
    "now": NOW,
}

WORKFLOW_ATTEMPT_REQUEST = {"run_id": RUN_1, "operation": "rewrite_data_files", "attempt": 2}

WORKFLOW_RECORD_RESULT_REQUEST = {
    "run_id": RUN_1,
    "operation": "rewrite_data_files",
    "attempt": 2,
    "succeeded": True,
    "metrics": {"completed_without_callback": 1},
    "error": None,
    "ended_by": "result",
    "still_running": False,
    "max_attempts": 5,
    "policy_id": GOLD_POLICY_ID,
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
    "reconciliation_id": REC_1,
    "reconciled_at": NOW,
    "wake_reasons": {"catalog_commit": 3},
    "table_uuid": "u1",
    "dry_run": False,
    "status": "planned",
    "skip_reason": None,
    "checks": WORKFLOW_CHECKS,
    "run_ids": {"rewrite_data_files": RUN_1},
    "run_start_failed": False,
    "policy_id": GOLD_POLICY_ID,
    "policy_name": "gold",
    "policy_version": 3,
    "policy_target": {"type": "namespace", "path": ["iceberg", "sales"]},
}


def test_create_runs_input_is_built_from_the_payload_the_reconciliation_workflow_sends():
    """The create runs input reads the workflow's payload: an ISO time, each run with its filters and arguments."""
    assert CreateTableMaintenanceRunsUseCaseInput.from_primitives(
        CREATE_REQUEST
    ) == CreateTableMaintenanceRunsUseCaseInput(
        table_uuid="u1",
        execution_ref="wf-r1",
        trigger="manual",
        priority="P1",
        now=NOW_DT,
        runs=(
            CreateTableMaintenanceRunsUseCaseInput.Run(
                run_id=RUN_1,
                operation="rewrite_data_files",
                filters=(CreateTableMaintenanceRunsUseCaseInput.Filter(spec_id=0, where="(`region` = 'eu')"),),
                procedure_args={"strategy": "binpack", "options": {"min-input-files": "5"}},
            ),
        ),
    )


def test_create_runs_input_reads_a_whole_table_payload_as_no_filters():
    """A run whose operation holds no filters, or names none, reads as no filters and no arguments."""
    whole_table = {**CREATE_REQUEST, "runs": [{**CREATE_RUN, "filters": [], "procedure_args": {}}]}
    built = CreateTableMaintenanceRunsUseCaseInput.from_primitives(whole_table).runs[0]
    assert (built.filters, built.procedure_args) == ((), {})
    bare = {**CREATE_REQUEST, "runs": [{"run_id": RUN_1, "operation": "rewrite_data_files"}]}
    assert CreateTableMaintenanceRunsUseCaseInput.from_primitives(bare).runs[0].filters == ()


def test_create_runs_activity_hands_the_use_case_the_input_built_from_the_payload():
    """The create runs activity builds its input with from_primitives."""
    create = FakeCreateRuns()
    activities = table_reconciliation_activities_with_fakes(create_runs=create)

    activities.create_maintenance_runs(dict(CREATE_REQUEST))

    assert create.requests == [CreateTableMaintenanceRunsUseCaseInput.from_primitives(CREATE_REQUEST)]


def test_submit_input_is_built_from_the_payload_the_maintenance_workflow_sends():
    """The submit input reads the workflow's payload with the worker's callback base URL added."""
    built = SubmitMaintenanceOperationUseCaseInput.from_primitives(
        {**WORKFLOW_SUBMIT_REQUEST, "callback_base_url": "http://cp:8000"}
    )

    assert built == SubmitMaintenanceOperationUseCaseInput(
        run_id=RUN_1,
        operation="rewrite_data_files",
        attempt=2,
        callback_base_url="http://cp:8000",
        now=NOW_DT,
        size="M",
    )


def test_submit_activity_hands_the_use_case_the_input_built_from_the_payload():
    """The submit activity adds its callback base URL to the payload and builds the input with from_primitives."""
    submit = FakeSubmit()
    activities = table_maintenance_activities_with_fakes(submit=submit)

    activities.submit_maintenance_operation(dict(WORKFLOW_SUBMIT_REQUEST))

    assert submit.requests == [
        SubmitMaintenanceOperationUseCaseInput.from_primitives(
            {**WORKFLOW_SUBMIT_REQUEST, "callback_base_url": "http://cp:8000"}
        )
    ]


def test_submit_activity_keeps_its_own_callback_base_url():
    """The callback base URL is the worker's setting, whatever the payload says."""
    submit = FakeSubmit()
    activities = table_maintenance_activities_with_fakes(submit=submit)

    activities.submit_maintenance_operation({**WORKFLOW_SUBMIT_REQUEST, "callback_base_url": "http://elsewhere"})

    assert submit.requests[0].callback_base_url == "http://cp:8000"


def test_submit_activity_refuses_a_mistyped_payload_without_retry():
    """A submit payload whose attempt is not an integer fails the activity at once."""
    submit = FakeSubmit()
    activities = table_maintenance_activities_with_fakes(submit=submit)

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
    activities = table_maintenance_activities_with_fakes(status=status, delete=delete)

    getattr(activities, activity)(dict(WORKFLOW_ATTEMPT_REQUEST))

    assert {"status": status, "delete": delete}[fake].requests == [
        input_type(run_id=RUN_1, operation="rewrite_data_files", attempt=2)
    ]
    assert input_type.from_primitives(WORKFLOW_ATTEMPT_REQUEST) == input_type(
        run_id=RUN_1, operation="rewrite_data_files", attempt=2
    )


def test_pods_input_is_built_from_the_payload_the_maintenance_workflow_sends():
    """The pods input reads the workflow's attempt triple."""
    assert GetMaintenanceJobPodsUseCaseInput.from_primitives(
        WORKFLOW_ATTEMPT_REQUEST
    ) == GetMaintenanceJobPodsUseCaseInput(run_id=RUN_1, operation="rewrite_data_files", attempt=2)


def test_pods_activity_refuses_a_payload_without_an_attempt_without_retry():
    """A pods payload missing its attempt fails the activity at once."""
    activities = table_maintenance_activities_with_fakes()

    with pytest.raises(ApplicationError) as caught:
        activities.get_maintenance_job_pods({"run_id": RUN_1, "operation": "rewrite_data_files"})

    assert caught.value.non_retryable
    assert caught.value.type == "InvariantViolation"


def test_record_result_input_is_built_from_the_payload_the_maintenance_workflow_sends():
    """The record result input reads every key the workflow sends, the planned policy included."""
    assert RecordTableMaintenanceOperationResultUseCaseInput.from_primitives(
        WORKFLOW_RECORD_RESULT_REQUEST
    ) == RecordTableMaintenanceOperationResultUseCaseInput(
        run_id=RUN_1,
        operation="rewrite_data_files",
        attempt=2,
        succeeded=True,
        metrics={"completed_without_callback": 1},
        error=None,
        now=NOW_DT,
        ended_by="result",
        still_running=False,
        max_attempts=5,
        policy_id=GOLD_POLICY_ID,
        policy_name="gold",
        policy_version=3,
        policy_target={"type": "table", "path": ["iceberg", "sales", "orders"], "table_uuid": "u1"},
    )


@pytest.mark.parametrize(
    "missing",
    ["ended_by", "still_running", "max_attempts", "policy_id", "policy_name", "policy_version", "policy_target"],
)
def test_record_result_input_requires_the_planned_policy(missing: str):
    """A record request without a key the maintenance workflow always sends is refused, naming the key."""
    request = {key: value for key, value in WORKFLOW_RECORD_RESULT_REQUEST.items() if key != missing}
    with pytest.raises(InvariantViolation, match=missing):
        RecordTableMaintenanceOperationResultUseCaseInput.from_primitives(request)


@pytest.mark.parametrize("key", ["policy_id", "policy_name", "policy_version"])
def test_record_result_input_refuses_a_planned_policy_without_its_value(key: str):
    """The planned policy's id, name and version are always known, so an empty one is refused."""
    with pytest.raises(InvariantViolation, match=key):
        RecordTableMaintenanceOperationResultUseCaseInput.from_primitives({**WORKFLOW_RECORD_RESULT_REQUEST, key: None})


def test_record_result_input_takes_the_platform_default_without_a_target():
    """The platform default is attached to nothing, so its record names no target."""
    built = RecordTableMaintenanceOperationResultUseCaseInput.from_primitives(
        {**WORKFLOW_RECORD_RESULT_REQUEST, "policy_target": None}
    )
    assert built.policy_target is None


def test_record_result_activity_hands_the_use_case_the_input_built_from_the_payload():
    """The record result activity builds its input with from_primitives and ignores a key a newer workflow adds."""
    record = FakeRecordResult()
    activities = table_maintenance_activities_with_fakes(record_result=record)

    activities.record_table_maintenance_operation_result({**WORKFLOW_RECORD_RESULT_REQUEST, "evidence_hint": "pods"})

    assert record.requests == [
        RecordTableMaintenanceOperationResultUseCaseInput.from_primitives(WORKFLOW_RECORD_RESULT_REQUEST)
    ]


def test_record_reconciliation_input_is_built_from_the_payload_the_reconciliation_workflow_sends():
    """The record input reads the workflow's payload: the plan's checks stay dicts, with lists inside."""
    built = RecordTableReconciliationUseCaseInput.from_primitives(WORKFLOW_RECORD_RECONCILIATION_REQUEST)

    assert built == RecordTableReconciliationUseCaseInput(
        reconciliation_id=REC_1,
        table_uuid="u1",
        reconciled_at=NOW_DT,
        wake_reasons={"catalog_commit": 3},
        dry_run=False,
        status="planned",
        skip_reason=None,
        checks=tuple(WORKFLOW_CHECKS),
        run_ids={"rewrite_data_files": RUN_1},
        run_start_failed=False,
        policy_id=GOLD_POLICY_ID,
        policy_name="gold",
        policy_version=3,
        policy_target={"type": "namespace", "path": ["iceberg", "sales"]},
    )


def test_record_reconciliation_activity_hands_the_use_case_the_input_built_from_the_payload():
    """The record reconciliation activity builds its input with from_primitives."""
    record = FakeRecordReconciliation()
    activities = table_reconciliation_activities_with_fakes(record=record)

    activities.record_table_reconciliation(dict(WORKFLOW_RECORD_RECONCILIATION_REQUEST))

    assert record.requests == [
        RecordTableReconciliationUseCaseInput.from_primitives(WORKFLOW_RECORD_RECONCILIATION_REQUEST)
    ]
