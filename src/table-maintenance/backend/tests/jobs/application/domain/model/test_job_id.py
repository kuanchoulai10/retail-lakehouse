from base import EntityId
from jobs.application.domain.model.job_id import JobId


def test_job_id_is_entity_id():
    assert issubclass(JobId, EntityId)


def test_job_id_value():
    jid = JobId(value="abc1234567")
    assert jid.value == "abc1234567"
    assert str(jid) == "abc1234567"


def test_job_id_equality():
    a = JobId(value="abc1234567")
    b = JobId(value="abc1234567")
    assert a == b


def test_job_id_inequality():
    a = JobId(value="abc1234567")
    b = JobId(value="xyz9876543")
    assert a != b
