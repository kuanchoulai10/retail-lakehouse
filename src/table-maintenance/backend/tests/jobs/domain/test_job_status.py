from datetime import UTC, datetime

from jobs.adapter.inbound.web.dto import JobResponse
from jobs.domain.job_status import JobStatus
from jobs.domain.job_type import JobType


def test_status_values():
    assert JobStatus.PENDING == "pending"
    assert JobStatus.RUNNING == "running"
    assert JobStatus.COMPLETED == "completed"
    assert JobStatus.FAILED == "failed"
    assert JobStatus.UNKNOWN == "unknown"


def test_job_response_fields():
    r = JobResponse(
        name="table-maintenance-rewrite-data-files-abc123",
        kind="SparkApplication",
        namespace="default",
        job_type=JobType.REWRITE_DATA_FILES,
        status=JobStatus.COMPLETED,
        created_at=datetime(2026, 4, 4, tzinfo=UTC),
    )
    assert r.name == "table-maintenance-rewrite-data-files-abc123"
    assert r.status == JobStatus.COMPLETED
