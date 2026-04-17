from datetime import UTC, datetime

from base import AggregateRoot
from application.domain.model.job import Job, JobId, JobType


def test_job_is_aggregate_root():
    assert issubclass(Job, AggregateRoot)


def test_job_fields():
    jid = JobId(value="abc1234567")
    job = Job(
        id=jid,
        job_type=JobType.REWRITE_DATA_FILES,
        created_at=datetime(2026, 4, 10, tzinfo=UTC),
        updated_at=datetime(2026, 4, 10, tzinfo=UTC),
        catalog="retail",
        table="inventory.orders",
        job_config={"rewrite_all": True},
    )
    assert job.id == jid
    assert job.job_type == JobType.REWRITE_DATA_FILES
    assert job.created_at == datetime(2026, 4, 10, tzinfo=UTC)
    assert job.updated_at == datetime(2026, 4, 10, tzinfo=UTC)
    assert job.catalog == "retail"
    assert job.table == "inventory.orders"
    assert job.job_config == {"rewrite_all": True}


def test_job_enabled_defaults_to_false():
    job = Job(
        id=JobId(value="abc1234567"),
        job_type=JobType.REWRITE_DATA_FILES,
        created_at=datetime(2026, 4, 10, tzinfo=UTC),
        updated_at=datetime(2026, 4, 10, tzinfo=UTC),
    )
    assert job.enabled is False


def test_job_enabled_can_be_true():
    job = Job(
        id=JobId(value="abc1234567"),
        job_type=JobType.REWRITE_DATA_FILES,
        created_at=datetime(2026, 4, 10, tzinfo=UTC),
        updated_at=datetime(2026, 4, 10, tzinfo=UTC),
        enabled=True,
    )
    assert job.enabled is True


def test_job_cron_defaults_to_none():
    job = Job(
        id=JobId(value="abc1234567"),
        job_type=JobType.REWRITE_DATA_FILES,
        created_at=datetime(2026, 4, 10, tzinfo=UTC),
        updated_at=datetime(2026, 4, 10, tzinfo=UTC),
        catalog="retail",
        table="inventory.orders",
        job_config={},
    )
    assert job.cron is None


def test_job_with_cron():
    job = Job(
        id=JobId(value="abc1234567"),
        job_type=JobType.REWRITE_DATA_FILES,
        created_at=datetime(2026, 4, 10, tzinfo=UTC),
        updated_at=datetime(2026, 4, 10, tzinfo=UTC),
        catalog="retail",
        table="inventory.orders",
        job_config={},
        cron="0 2 * * *",
    )
    assert job.cron == "0 2 * * *"


def test_job_equality_by_id():
    a = Job(
        id=JobId("abc1234567"),
        job_type=JobType.REWRITE_DATA_FILES,
        created_at=datetime(2026, 4, 10, tzinfo=UTC),
        updated_at=datetime(2026, 4, 10, tzinfo=UTC),
    )
    b = Job(
        id=JobId("abc1234567"),
        job_type=JobType.EXPIRE_SNAPSHOTS,
        created_at=datetime(2026, 4, 11, tzinfo=UTC),
        updated_at=datetime(2026, 4, 11, tzinfo=UTC),
    )
    assert a == b


def test_job_inequality_different_id():
    a = Job(
        id=JobId("abc1234567"),
        job_type=JobType.REWRITE_DATA_FILES,
        created_at=datetime(2026, 4, 10, tzinfo=UTC),
        updated_at=datetime(2026, 4, 10, tzinfo=UTC),
    )
    b = Job(
        id=JobId("xyz9876543"),
        job_type=JobType.REWRITE_DATA_FILES,
        created_at=datetime(2026, 4, 10, tzinfo=UTC),
        updated_at=datetime(2026, 4, 10, tzinfo=UTC),
    )
    assert a != b
