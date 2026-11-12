"""Test how recording an attempt's result classifies the failure, decides the next attempt and remembers it."""

from __future__ import annotations

from typing import Any

import pytest

from context.table_maintenance.application.domain.model.shared import (
    ComputeSize,
    MaintenanceOperation,
)
from context.table_maintenance.application.domain.model.table import (
    AppliedPolicyRef,
    Table,
    TableId,
    TableName,
)
from context.table_maintenance.application.domain.model.table_discovery_rules import (
    TableDiscoveryRuleId,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy import DEFAULT_POLICY_NAME
from context.table_maintenance.application.domain.model.table_maintenance_run import (
    FailureClass,
    NextStep,
    TableMaintenanceRun,
    TableMaintenanceRunId,
    TriggerType,
)
from context.table_maintenance.application.exceptions import ValidationError
from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    RecordTableMaintenanceOperationResultUseCaseInput,
)
from context.table_maintenance.application.port.outbound.table_maintenance_run import (
    JobContainerExit,
    ReadMaintenanceJobEvidenceGatewayOutput,
)
from context.table_maintenance.application.service.table_maintenance_run import (
    RecordTableMaintenanceOperationResultService,
)
from tests.context.table_maintenance.fakes.scripted_read_maintenance_event_log_gateway import (
    ScriptedReadMaintenanceEventLogGateway,
)
from tests.context.table_maintenance.fakes.scripted_read_maintenance_job_evidence_gateway import (
    ScriptedReadMaintenanceJobEvidenceGateway,
)
from tests.context.table_maintenance.fakes.track_calls import track_calls

RDF = MaintenanceOperation.REWRITE_DATA_FILES
APP_ID = "spark-0001"
OOM = "Py4JJavaError: An error occurred. java.lang.OutOfMemoryError: Java heap space"


@pytest.fixture
def table(tables_repo, now) -> Table:
    """Provide a stored managed table."""
    t = Table.register(
        TableId("u-1"), TableName(catalog="iceberg", namespace="sales", table="orders"), TableDiscoveryRuleId("r"), now
    )
    tables_repo.create(t)
    return t


@pytest.fixture
def evidence() -> ScriptedReadMaintenanceJobEvidenceGateway:
    """Provide the scripted evidence gateway."""
    return ScriptedReadMaintenanceJobEvidenceGateway()


@pytest.fixture
def event_log() -> ScriptedReadMaintenanceEventLogGateway:
    """Provide the scripted event log gateway."""
    return ScriptedReadMaintenanceEventLogGateway()


@pytest.fixture
def resolve_calls(resolve_applicable_policy) -> list[Any]:
    """Record every call of the applicable policy resolution."""
    calls: list[Any] = []
    original = resolve_applicable_policy.execute

    def execute(request: Any) -> Any:  # noqa: ANN401
        calls.append(request)
        return original(request)

    resolve_applicable_policy.execute = execute
    return calls


@pytest.fixture
def recorder(runs_repo, tables_repo, evidence, event_log, resolve_applicable_policy, resolve_calls):
    """Provide the record service on the fakes."""
    return RecordTableMaintenanceOperationResultService(
        runs_repo, tables_repo, evidence, event_log, resolve_applicable_policy
    )


def _run(runs_repo, table, now, *sizes: ComputeSize) -> TableMaintenanceRun:
    """Store a run whose rewrite operation has failed every size but the last, which is running."""
    run = TableMaintenanceRun.create(
        TableMaintenanceRunId("run-1"), table.id, TriggerType.SCHEDULED, [RDF], now, execution_ref="wf-1"
    )
    for attempt, size in enumerate(sizes, start=1):
        if attempt > 1:
            run.fail(RDF, attempt - 1, "earlier", now)
        run.start_attempt(RDF, attempt, f"job-{attempt}", now, size=size)
    runs_repo.create(run)
    return run


def _record(recorder, now, **overrides):
    fields: dict[str, Any] = {
        "run_id": "run-1",
        "operation": "rewrite_data_files",
        "attempt": 1,
        "succeeded": False,
        "metrics": {},
        "error": OOM,
        "now": now,
    }
    fields.update(overrides)
    return recorder.execute(RecordTableMaintenanceOperationResultUseCaseInput(**fields))


def _evidence(execution_id: str | None = APP_ID, error: str | None = None, *containers: JobContainerExit):
    return ReadMaintenanceJobEvidenceGatewayOutput(execution_id=execution_id, error=error, containers=containers)


def test_oom_text_is_classified_and_retried_at_the_next_size(recorder, runs_repo, table, now):
    """An OutOfMemoryError at S is an OOM, retried at M; the attempt keeps the class, decision and raw error."""
    _run(runs_repo, table, now, ComputeSize.S)
    out = _record(recorder, now)
    assert (out.failure_class, out.next_step, out.next_size) == ("oom", "retry_larger", "M")
    record = runs_repo.get(TableMaintenanceRunId("run-1")).attempt_record(RDF, 1)
    assert (record.failure_class, record.next_step, record.next_size, record.error) == (
        FailureClass.OOM,
        NextStep.RETRY_LARGER,
        ComputeSize.M,
        OOM,
    )


def test_executor_oom_kill_is_read_from_the_job_evidence(recorder, runs_repo, table, evidence, now):
    """An executor killed for memory makes an otherwise vague failure an OOM."""
    _run(runs_repo, table, now, ComputeSize.S)
    killed = JobContainerExit(role="executor", reason="OOMKilled", exit_code=137, message=None)
    evidence.set_evidence("run-1", "rewrite_data_files", 1, _evidence(APP_ID, None, killed))
    out = _record(recorder, now, error="RuntimeError: rewrite_data_files failed: no file group was committed")
    assert out.failure_class == "oom"


def test_a_driver_termination_message_is_read_as_text(recorder, runs_repo, table, evidence, now):
    """A driver that left an OutOfMemoryError in its termination message failed of OOM."""
    _run(runs_repo, table, now, ComputeSize.S)
    driver = JobContainerExit(role="driver", reason="Error", exit_code=1, message="java.lang.OutOfMemoryError")
    evidence.set_evidence("run-1", "rewrite_data_files", 1, _evidence(APP_ID, "driver failed", driver))
    assert _record(recorder, now, error="spark job failed", ended_by="job_failed").failure_class == "oom"


def test_event_log_state_is_recorded_on_the_attempt(recorder, runs_repo, table, evidence, event_log, now):
    """The event log state is recorded on failures and successes; without an execution id it is unknown."""
    _run(runs_repo, table, now, ComputeSize.S)
    evidence.set_evidence("run-1", "rewrite_data_files", 1, _evidence())
    event_log.finished[APP_ID] = False
    _record(recorder, now)
    assert runs_repo.get(TableMaintenanceRunId("run-1")).attempt_record(RDF, 1).event_log_finished is False

    run = runs_repo.get(TableMaintenanceRunId("run-1"))
    run.start_attempt(RDF, 2, "job-2", now, size=ComputeSize.M)
    runs_repo.update(run)
    evidence.set_evidence("run-1", "rewrite_data_files", 2, _evidence("spark-0002"))
    event_log.finished["spark-0002"] = True
    _record(recorder, now, attempt=2, succeeded=True, error=None)
    assert runs_repo.get(TableMaintenanceRunId("run-1")).attempt_record(RDF, 2).event_log_finished is True
    assert len(event_log.calls) == 2


def test_no_execution_id_leaves_the_event_log_unknown_without_reading_it(recorder, runs_repo, table, event_log, now):
    """An attempt whose job has no execution id records an unknown event log state and reads no log."""
    _run(runs_repo, table, now, ComputeSize.S)
    _record(recorder, now)
    assert runs_repo.get(TableMaintenanceRunId("run-1")).attempt_record(RDF, 1).event_log_finished is None
    assert event_log.calls == []


@pytest.mark.parametrize("ended_by", ["timed_out", "cancelled", "missing", "submit_failed", "admission_failed"])
def test_evidence_is_not_read_for_attempts_spark_did_not_end(
    recorder, runs_repo, table, evidence, event_log, now, ended_by
):
    """Only an attempt that Spark itself ended (its report, or a failed job) has evidence worth reading."""
    _run(runs_repo, table, now, ComputeSize.S)
    _record(recorder, now, error="spark job timed out", ended_by=ended_by)
    assert evidence.calls == []
    assert event_log.calls == []


def test_timed_out_attempt_is_timeout_and_retries_at_the_same_size(recorder, runs_repo, table, now):
    """A timed-out attempt is a timeout, retried at its size."""
    _run(runs_repo, table, now, ComputeSize.M)
    out = _record(recorder, now, error="spark job timed out", ended_by="timed_out")
    assert (out.failure_class, out.next_step, out.next_size) == ("timeout", "retry_same", "M")


def test_unreadable_evidence_still_records_the_attempt(recorder, runs_repo, table, evidence, event_log, now):
    """When the evidence cannot be read the attempt is classified from its error text and still saved."""
    _run(runs_repo, table, now, ComputeSize.S)
    evidence.error = RuntimeError("k8s down")
    out = _record(recorder, now)
    assert out.failure_class == "oom"
    record = runs_repo.get(TableMaintenanceRunId("run-1")).attempt_record(RDF, 1)
    assert record.status.value == "failed"
    assert record.event_log_finished is None
    assert event_log.calls == []


def test_unreadable_event_log_still_records_the_attempt(recorder, runs_repo, table, evidence, event_log, now):
    """When the event log cannot be read its state is unknown and the attempt is still saved."""
    _run(runs_repo, table, now, ComputeSize.S)
    evidence.set_evidence("run-1", "rewrite_data_files", 1, _evidence())
    event_log.error = OSError("rustfs down")
    _record(recorder, now)
    assert runs_repo.get(TableMaintenanceRunId("run-1")).attempt_record(RDF, 1).event_log_finished is None


def test_oom_at_l_marks_the_operation_needs_attention_under_the_applicable_policy(
    recorder, runs_repo, tables_repo, table, resolve_calls, now
):
    """An OOM at the largest size stops and marks the table's operation under the policy that applies."""
    _run(runs_repo, table, now, ComputeSize.M, ComputeSize.L)
    out = _record(recorder, now, attempt=2)
    assert (out.failure_class, out.next_step, out.next_size) == ("oom", "needs_attention", None)
    mark = tables_repo.get(TableId("u-1")).operation_state(RDF).attention
    assert mark is not None
    assert mark.since == now
    assert mark.reason == "out of memory at size L"
    assert mark.policy == AppliedPolicyRef(name=DEFAULT_POLICY_NAME, version=1, target=None)
    assert len(resolve_calls) == 1


def test_oom_below_l_does_not_resolve_the_policy(recorder, runs_repo, table, resolve_calls, now):
    """Only a needs-attention decision resolves the applicable policy."""
    _run(runs_repo, table, now, ComputeSize.S)
    _record(recorder, now)
    assert resolve_calls == []


def test_still_running_failure_stops(recorder, runs_repo, table, now):
    """An attempt whose job may still run is not retried, whatever its class."""
    _run(runs_repo, table, now, ComputeSize.S)
    out = _record(recorder, now, error="spark job timed out", ended_by="timed_out", still_running=True)
    assert (out.failure_class, out.next_step, out.next_size) == ("timeout", "still_running", None)


def test_last_attempt_uses_up_the_attempts(recorder, runs_repo, table, now):
    """The last allowed attempt of a same-size failure stops."""
    _run(runs_repo, table, now, ComputeSize.S, ComputeSize.S, ComputeSize.S)
    out = _record(recorder, now, attempt=3, error="boom", max_attempts=3)
    assert out.next_step == "attempts_used"


def test_replayed_record_returns_the_stored_decision(
    recorder, runs_repo, tables_repo, table, evidence, event_log, resolve_calls, log, now
):
    """A retried record returns the decision it stored and reads and saves nothing again."""
    _run(runs_repo, table, now, ComputeSize.M, ComputeSize.L)
    evidence.set_evidence("run-1", "rewrite_data_files", 2, _evidence())
    track_calls(tables_repo, "update", "tables.update", log, lambda t: t.id.value)
    first = _record(recorder, now, attempt=2)
    second = _record(recorder, now, attempt=2)
    assert first == second
    assert (second.failure_class, second.next_step) == ("oom", "needs_attention")
    assert len(evidence.calls) == 1
    assert len(event_log.calls) == 1
    assert len(resolve_calls) == 1
    assert log == [("tables.update", "u-1")]


def test_a_stale_attempt_returns_its_stored_decision(recorder, runs_repo, table, now):
    """A record for an earlier attempt returns what was decided for it."""
    run = _run(runs_repo, table, now, ComputeSize.S)
    _record(recorder, now)
    run = runs_repo.get(run.id)
    run.start_attempt(RDF, 2, "job-2", now, size=ComputeSize.M)
    runs_repo.update(run)
    out = _record(recorder, now, error="late", attempt=1)
    assert (out.failure_class, out.next_step, out.next_size) == ("oom", "retry_larger", "M")


def test_success_remembers_the_size_on_the_table(recorder, runs_repo, tables_repo, table, now):
    """A success at M makes M the table's start size for the operation."""
    _run(runs_repo, table, now, ComputeSize.S, ComputeSize.M)
    out = _record(recorder, now, attempt=2, succeeded=True, error=None, metrics={"rewritten_data_files_count": 2})
    assert (out.failure_class, out.next_step, out.next_size) == (None, "done", None)
    assert tables_repo.get(TableId("u-1")).operation_state(RDF).start_size() is ComputeSize.M


def test_unknown_ending_is_refused(recorder, runs_repo, table, now):
    """An ending outside the known ones is a validation error."""
    _run(runs_repo, table, now, ComputeSize.S)
    with pytest.raises(ValidationError):
        _record(recorder, now, ended_by="exploded")
