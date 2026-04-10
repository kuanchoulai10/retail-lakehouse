from jobs.domain.job_status import JobStatus


def test_status_values():
    assert JobStatus.PENDING == "pending"
    assert JobStatus.RUNNING == "running"
    assert JobStatus.COMPLETED == "completed"
    assert JobStatus.FAILED == "failed"
    assert JobStatus.UNKNOWN == "unknown"
