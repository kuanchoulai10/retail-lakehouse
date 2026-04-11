from datetime import UTC, datetime

from jobs.application.domain.model.job import Job
from jobs.application.domain.model.job_id import JobId
from jobs.application.domain.model.job_status import JobStatus
from jobs.application.domain.model.job_type import JobType


def test_status_values():
    assert JobStatus.PENDING == "pending"
    assert JobStatus.RUNNING == "running"
    assert JobStatus.COMPLETED == "completed"
    assert JobStatus.FAILED == "failed"
    assert JobStatus.UNKNOWN == "unknown"


def test_job_fields():
    job = Job(
        id=JobId(value="abc1234567"),
        job_type=JobType.REWRITE_DATA_FILES,
        status=JobStatus.COMPLETED,
        created_at=datetime(2026, 4, 4, tzinfo=UTC),
    )
    assert job.id.value == "abc1234567"
    assert job.status == JobStatus.COMPLETED
