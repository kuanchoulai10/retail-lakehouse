from application.domain.model.job_run_status import JobRunStatus


def test_enum_values():
    assert JobRunStatus.PENDING == "pending"
    assert JobRunStatus.RUNNING == "running"
    assert JobRunStatus.COMPLETED == "completed"
    assert JobRunStatus.FAILED == "failed"
    assert JobRunStatus.UNKNOWN == "unknown"
