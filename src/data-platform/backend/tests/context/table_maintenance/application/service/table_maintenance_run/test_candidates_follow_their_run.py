"""Test that the compaction candidates a run claimed move on with its compaction."""

from __future__ import annotations

from datetime import timedelta

import pytest

from context.table_maintenance.application.domain.model.compaction_candidate import (
    CandidateScore,
    CandidateState,
    CompactionCandidate,
    PartitionKey,
)
from context.table_maintenance.application.domain.model.shared import MaintenanceOperation
from context.table_maintenance.application.domain.model.table import Table, TableId, TableName
from context.table_maintenance.application.domain.model.table_discovery_rules import TableDiscoveryRuleId
from context.table_maintenance.application.domain.model.table_maintenance_run import (
    TableMaintenanceRun,
    TableMaintenanceRunId,
    TriggerType,
)
from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    RecordTableMaintenanceOperationResultUseCaseInput,
    SubmitMaintenanceOperationUseCaseInput,
)
from context.table_maintenance.application.service.table_maintenance_run import (
    RecordTableMaintenanceOperationResultService,
    SubmitMaintenanceOperationService,
)
from tests.context.table_maintenance.fakes.scripted_read_maintenance_event_log_gateway import (
    ScriptedReadMaintenanceEventLogGateway,
)
from tests.context.table_maintenance.fakes.scripted_read_maintenance_job_evidence_gateway import (
    ScriptedReadMaintenanceJobEvidenceGateway,
)

RUN_1 = "mr-00000000000000000000000001"
RUN_2 = "mr-00000000000000000000000002"

RDF = MaintenanceOperation.REWRITE_DATA_FILES
EXPIRE = MaintenanceOperation.EXPIRE_SNAPSHOTS
RUN = TableMaintenanceRunId(RUN_1)
OTHER = TableMaintenanceRunId(RUN_2)
SCORE = CandidateScore(reducible_files=10, data_bytes=1000, estimated_gb_hours=0.1, score=0.5)


def _candidate(value: str, run: TableMaintenanceRunId | None, now):  # noqa: ANN001, ANN202
    candidate = CompactionCandidate.create(
        table_uuid=TableId("u-1"),
        partition=PartitionKey(spec_id=0, values=(value,)),
        label=f"region={value}",
        score=SCORE,
        last_written_at=None,
        hold_reason=None,
        now=now,
    )
    if run is not None:
        candidate.grant("round-1", now + timedelta(minutes=10), now)
        candidate.claim(run, now + timedelta(hours=20), now)
    return candidate


@pytest.fixture
def setup(tables_repo, runs_repo, candidates_repo, now):  # noqa: ANN001, ANN201
    """Store a table, a run of compaction and expiry, and candidates of this run, of another run and free."""
    tables_repo.create(
        Table.register(
            TableId("u-1"),
            TableName(catalog="iceberg", namespace="sales", table="orders"),
            TableDiscoveryRuleId.new(),
            now,
        )
    )
    runs_repo.create(
        TableMaintenanceRun.create(RUN, TableId("u-1"), TriggerType.SCHEDULED, [RDF, EXPIRE], now, execution_ref="wf")
    )
    candidates_repo.save_all([_candidate("eu", RUN, now), _candidate("us", RUN, now), _candidate("ap", OTHER, now)])
    candidates_repo.save_all([_candidate("sa", None, now)])


@pytest.fixture
def submitter(runs_repo, tables_repo, submit_job, candidates_repo):  # noqa: ANN001, ANN201
    """Provide the submit service on the fakes."""
    return SubmitMaintenanceOperationService(runs_repo, tables_repo, submit_job, candidates_repo=candidates_repo)


@pytest.fixture
def recorder(runs_repo, tables_repo, resolve_applicable_policy, candidates_repo):  # noqa: ANN001, ANN201
    """Provide the record service on the fakes."""
    return RecordTableMaintenanceOperationResultService(
        runs_repo,
        tables_repo,
        ScriptedReadMaintenanceJobEvidenceGateway(),
        ScriptedReadMaintenanceEventLogGateway(),
        resolve_applicable_policy,
        size_memory={},
        candidates_repo=candidates_repo,
    )


def _submit(submitter, now, operation=RDF, attempt=1):  # noqa: ANN001, ANN202
    return submitter.execute(
        SubmitMaintenanceOperationUseCaseInput(
            run_id=RUN.value,
            operation=operation.value,
            attempt=attempt,
            filters=(),
            procedure_args={},
            callback_base_url="http://cp",
            now=now,
        )
    )


def _record(recorder, now, *, succeeded, attempt=1, error=None, operation=RDF):  # noqa: ANN001, ANN202
    return recorder.execute(
        RecordTableMaintenanceOperationResultUseCaseInput(
            run_id=RUN.value,
            operation=operation.value,
            attempt=attempt,
            succeeded=succeeded,
            metrics={},
            error=error,
            now=now,
        )
    )


def _states(candidates_repo) -> dict[str, CandidateState]:  # noqa: ANN001
    return {str(c.partition.values[0]): c.state for c in candidates_repo.list_all()}


@pytest.mark.usefixtures("setup")
def test_first_submit_starts_the_claimed_candidates(submitter, candidates_repo, now):
    """Submitting the run's compaction starts the candidates it claimed, and only those."""
    _submit(submitter, now)

    assert _states(candidates_repo) == {
        "eu": CandidateState.RUNNING,
        "us": CandidateState.RUNNING,
        "ap": CandidateState.CLAIMED,
        "sa": CandidateState.PENDING,
    }


@pytest.mark.usefixtures("setup")
def test_submit_of_another_operation_leaves_candidates_alone(submitter, candidates_repo, now):
    """Only compaction moves candidates."""
    _submit(submitter, now, operation=EXPIRE)

    assert _states(candidates_repo)["eu"] is CandidateState.CLAIMED


@pytest.mark.usefixtures("setup")
def test_succeeded_compaction_marks_its_candidates_done(submitter, recorder, candidates_repo, now):
    """A compaction that succeeded ends its candidates as done."""
    _submit(submitter, now)

    _record(recorder, now + timedelta(minutes=5), succeeded=True)

    states = _states(candidates_repo)
    assert (states["eu"], states["us"], states["ap"]) == (
        CandidateState.DONE,
        CandidateState.DONE,
        CandidateState.CLAIMED,
    )


@pytest.mark.usefixtures("setup")
def test_finally_failed_compaction_marks_its_candidates_failed(submitter, recorder, candidates_repo, now):
    """A compaction whose last attempt failed ends its candidates as failed."""
    for attempt in (1, 2, 3):
        _submit(submitter, now, attempt=attempt)
        _record(recorder, now, succeeded=False, attempt=attempt, error="boom")

    assert _states(candidates_repo)["eu"] is CandidateState.FAILED


@pytest.mark.usefixtures("setup")
def test_retried_attempt_leaves_candidates_running(submitter, recorder, candidates_repo, now):
    """A failed attempt that will be retried leaves the candidates running."""
    _submit(submitter, now)

    out = _record(recorder, now, succeeded=False, error="java.lang.OutOfMemoryError: Java heap space")

    assert out.next_step == "retry_larger"
    assert _states(candidates_repo)["eu"] is CandidateState.RUNNING


@pytest.mark.usefixtures("setup")
def test_a_replayed_result_still_finishes_the_candidates(submitter, recorder, candidates_repo, runs_repo, now):
    """A result recorded on the run whose candidates were not finished yet (a crash between) finishes them."""
    _submit(submitter, now)
    run = runs_repo.get(RUN)
    run.succeed(RDF, 1, {}, now)
    runs_repo.update(run)

    _record(recorder, now, succeeded=True)

    assert _states(candidates_repo)["eu"] is CandidateState.DONE
