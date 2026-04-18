from __future__ import annotations

from datetime import UTC, datetime

from adapter.outbound.job_run.sql.row_to_job_run import row_to_job_run
from application.domain.model.job import JobId
from application.domain.model.job_run import JobRun, JobRunId, JobRunStatus


def test_deserializes_row_to_job_run():
    row = {
        "id": "run-1",
        "job_id": "job-1",
        "status": "running",
        "started_at": datetime(2026, 4, 10, 12, 0, tzinfo=UTC),
        "finished_at": None,
    }
    run = row_to_job_run(row)
    assert isinstance(run, JobRun)
    assert run.id == JobRunId(value="run-1")
    assert run.job_id == JobId(value="job-1")
    assert run.status == JobRunStatus.RUNNING
    assert run.started_at == datetime(2026, 4, 10, 12, 0, tzinfo=UTC)
    assert run.finished_at is None


def test_deserializes_all_statuses():
    for status in JobRunStatus:
        row = {
            "id": "r",
            "job_id": "j",
            "status": status.value,
            "started_at": None,
            "finished_at": None,
        }
        assert row_to_job_run(row).status == status
