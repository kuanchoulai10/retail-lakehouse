"""Tests for SubmitJobRunService."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from application.domain.model.job import JobId
from application.domain.model.job_run import JobRun, JobRunId, JobRunStatus
from application.port.inbound.job_run.submit_job_run import (
    SubmitJobRunUseCaseInput,
    SubmitJobRunUseCase,
)
from application.port.outbound.job_run.submit_job_run.input import (
    SubmitJobRunGatewayInput,
)
from application.service.job_run.submit_job_run import SubmitJobRunService
from adapter.outbound.job_run.job_runs_in_memory_repo import JobRunsInMemoryRepo


def _make_input(**overrides) -> SubmitJobRunUseCaseInput:
    defaults = {
        "run_id": "r1",
        "job_id": "j1",
        "job_type": "compaction",
        "catalog": "warehouse",
        "table": "orders",
        "job_config": {"option": "value"},
        "driver_memory": "1g",
        "executor_memory": "2g",
        "executor_instances": 3,
        "cron_expression": "0 0 * * *",
    }
    defaults.update(overrides)
    return SubmitJobRunUseCaseInput(**defaults)


def _pending_job_run(run_id: str = "r1") -> JobRun:
    return JobRun(
        id=JobRunId(value=run_id),
        job_id=JobId(value="j1"),
        status=JobRunStatus.PENDING,
        started_at=datetime(2026, 4, 28, 12, 0, tzinfo=UTC),
    )


class TestSubmitJobRunService:
    """Tests for SubmitJobRunService."""

    def test_submits_job_with_correct_mapping(self) -> None:
        executor = MagicMock()
        repo = MagicMock()
        service = SubmitJobRunService(executor, repo)
        inp = _make_input()

        service.execute(inp)

        executor.submit.assert_called_once_with(
            SubmitJobRunGatewayInput(
                run_id="r1",
                job_id="j1",
                job_type="compaction",
                catalog="warehouse",
                table="orders",
                job_config={"option": "value"},
                driver_memory="1g",
                executor_memory="2g",
                executor_instances=3,
                cron_expression="0 0 * * *",
            )
        )

    def test_submits_job_with_no_cron(self) -> None:
        executor = MagicMock()
        repo = MagicMock()
        service = SubmitJobRunService(executor, repo)
        inp = _make_input(cron_expression=None)

        service.execute(inp)

        submission = executor.submit.call_args[0][0]
        assert submission.cron_expression is None

    def test_implements_use_case_interface(self) -> None:
        executor = MagicMock()
        repo = MagicMock()
        service = SubmitJobRunService(executor, repo)
        assert isinstance(service, SubmitJobRunUseCase)


class TestSubmitJobRunServiceMarksRunning:
    def test_marks_job_run_as_running_after_submit(self) -> None:
        executor = MagicMock()
        repo = JobRunsInMemoryRepo()
        repo.create(_pending_job_run())
        service = SubmitJobRunService(executor, repo)
        inp = _make_input()

        service.execute(inp)

        saved = repo.get(JobRunId(value="r1"))
        assert saved.status == JobRunStatus.RUNNING

    def test_does_not_mark_running_if_submit_fails(self) -> None:
        executor = MagicMock()
        executor.submit.side_effect = RuntimeError("K8s unreachable")
        repo = JobRunsInMemoryRepo()
        repo.create(_pending_job_run())
        service = SubmitJobRunService(executor, repo)
        inp = _make_input()

        with pytest.raises(RuntimeError):
            service.execute(inp)

        saved = repo.get(JobRunId(value="r1"))
        assert saved.status == JobRunStatus.PENDING
