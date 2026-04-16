from datetime import UTC, datetime

from application.domain.model.job import Job
from application.domain.model.job_id import JobId
from application.domain.model.job_status import JobStatus
from application.domain.model.job_type import JobType


def test_status_values():
    assert JobStatus.PENDING == "pending"
    assert JobStatus.RUNNING == "running"
    assert JobStatus.COMPLETED == "completed"
    assert JobStatus.FAILED == "failed"
    assert JobStatus.UNKNOWN == "unknown"


def test_job_fields():
    ts = datetime(2026, 4, 4, tzinfo=UTC)
    job = Job(
        id=JobId(value="abc1234567"),
        job_type=JobType.REWRITE_DATA_FILES,
        status=JobStatus.COMPLETED,
        created_at=ts,
        updated_at=ts,
    )
    assert job.id.value == "abc1234567"
    assert job.status == JobStatus.COMPLETED
