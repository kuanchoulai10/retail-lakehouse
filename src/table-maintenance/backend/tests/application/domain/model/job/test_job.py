"""Tests for Job."""

from datetime import UTC, datetime

from core.base import AggregateRoot
from core.application.domain.model.job import (
    CronExpression,
    Job,
    JobId,
    JobStatus,
    JobType,
    TableReference,
)


def test_job_is_aggregate_root():
    """Verify that Job is a subclass of AggregateRoot."""
    assert issubclass(Job, AggregateRoot)


def test_job_fields():
    """Verify that all Job fields are stored correctly."""
    jid = JobId(value="abc1234567")
    job = Job(
        id=jid,
        job_type=JobType.REWRITE_DATA_FILES,
        created_at=datetime(2026, 4, 10, tzinfo=UTC),
        updated_at=datetime(2026, 4, 10, tzinfo=UTC),
        table_ref=TableReference(catalog="retail", table="inventory.orders"),
        job_config={"rewrite_all": True},
    )
    assert job.id == jid
    assert job.job_type == JobType.REWRITE_DATA_FILES
    assert job.created_at == datetime(2026, 4, 10, tzinfo=UTC)
    assert job.updated_at == datetime(2026, 4, 10, tzinfo=UTC)
    assert job.table_ref.catalog == "retail"
    assert job.table_ref.table == "inventory.orders"
    assert job.job_config == {"rewrite_all": True}


def test_job_status_defaults_to_active():
    """Verify that status defaults to ACTIVE when not specified."""
    job = Job(
        id=JobId(value="abc1234567"),
        job_type=JobType.REWRITE_DATA_FILES,
        created_at=datetime(2026, 4, 10, tzinfo=UTC),
        updated_at=datetime(2026, 4, 10, tzinfo=UTC),
    )
    assert job.status == JobStatus.ACTIVE


def test_job_status_can_be_paused():
    """Verify that status can be set to PAUSED."""
    job = Job(
        id=JobId(value="abc1234567"),
        job_type=JobType.REWRITE_DATA_FILES,
        created_at=datetime(2026, 4, 10, tzinfo=UTC),
        updated_at=datetime(2026, 4, 10, tzinfo=UTC),
        status=JobStatus.PAUSED,
    )
    assert job.status == JobStatus.PAUSED


def test_job_cron_defaults_to_none():
    """Verify that cron defaults to None when not specified."""
    job = Job(
        id=JobId(value="abc1234567"),
        job_type=JobType.REWRITE_DATA_FILES,
        created_at=datetime(2026, 4, 10, tzinfo=UTC),
        updated_at=datetime(2026, 4, 10, tzinfo=UTC),
        table_ref=TableReference(catalog="retail", table="inventory.orders"),
        job_config={},
    )
    assert job.cron is None


def test_job_with_cron():
    """Verify that cron expression is stored when provided."""
    job = Job(
        id=JobId(value="abc1234567"),
        job_type=JobType.REWRITE_DATA_FILES,
        created_at=datetime(2026, 4, 10, tzinfo=UTC),
        updated_at=datetime(2026, 4, 10, tzinfo=UTC),
        table_ref=TableReference(catalog="retail", table="inventory.orders"),
        job_config={},
        cron=CronExpression(expression="0 2 * * *"),
    )
    assert job.cron == CronExpression(expression="0 2 * * *")


def test_job_equality_by_id():
    """Verify that two Jobs with the same id are equal regardless of other fields."""
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
    """Verify that two Jobs with different ids are not equal."""
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


def test_job_defaults_next_run_at_to_none():
    """Verify that next_run_at defaults to None when not specified."""
    job = Job(
        id=JobId("abc1234567"),
        job_type=JobType.REWRITE_DATA_FILES,
        created_at=datetime(2026, 4, 10, tzinfo=UTC),
        updated_at=datetime(2026, 4, 10, tzinfo=UTC),
    )
    assert job.next_run_at is None


def test_job_defaults_max_active_runs_to_1():
    """Verify that max_active_runs defaults to 1 when not specified."""
    job = Job(
        id=JobId("abc1234567"),
        job_type=JobType.REWRITE_DATA_FILES,
        created_at=datetime(2026, 4, 10, tzinfo=UTC),
        updated_at=datetime(2026, 4, 10, tzinfo=UTC),
    )
    assert job.max_active_runs == 1


def test_job_with_scheduling_fields():
    """Verify that next_run_at and max_active_runs are stored when provided."""
    run_at = datetime(2026, 4, 22, 10, 0, tzinfo=UTC)
    job = Job(
        id=JobId("abc1234567"),
        job_type=JobType.REWRITE_DATA_FILES,
        created_at=datetime(2026, 4, 10, tzinfo=UTC),
        updated_at=datetime(2026, 4, 10, tzinfo=UTC),
        cron=CronExpression(expression="0 10 * * *"),
        next_run_at=run_at,
        max_active_runs=3,
    )
    assert job.next_run_at == run_at
    assert job.max_active_runs == 3
