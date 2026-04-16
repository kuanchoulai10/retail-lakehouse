from application.domain.model.job_id import JobId
from application.domain.model.job_run_id import JobRunId
from base.entity_id import EntityId


def test_is_entity_id():
    assert issubclass(JobRunId, EntityId)


def test_equality_by_value():
    a = JobRunId(value="run-1")
    b = JobRunId(value="run-1")
    assert a == b


def test_inequality_different_value():
    a = JobRunId(value="run-1")
    b = JobRunId(value="run-2")
    assert a != b


def test_typed_distinct_from_job_id():
    run_id = JobRunId(value="same-value")
    job_id = JobId(value="same-value")
    assert run_id != job_id
