"""Tests for JobRun domain events."""

from datetime import UTC, datetime

from base import DomainEvent
from application.domain.model.job import (
    CronExpression,
    JobId,
    JobType,
    ResourceConfig,
    TableReference,
)
from application.domain.model.job_run import JobRunId, TriggerType
from application.domain.model.job_run.job_run_result import JobRunResult
from application.domain.model.job_run.events import (
    JobRunCancelled,
    JobRunCompleted,
    JobRunCreated,
    JobRunFailed,
    JobRunStarted,
)


class TestJobRunCreated:
    """Tests for JobRunCreated event."""

    def test_is_domain_event(self):
        assert issubclass(JobRunCreated, DomainEvent)

    def test_fields(self):
        rc = ResourceConfig(
            driver_memory="2g", executor_memory="4g", executor_instances=2
        )
        ev = JobRunCreated(
            run_id=JobRunId(value="r1"),
            job_id=JobId(value="j1"),
            trigger_type=TriggerType.MANUAL,
            job_type=JobType.EXPIRE_SNAPSHOTS,
            table_ref=TableReference(catalog="cat", table="tbl"),
            job_config={"retain_last": 5},
            resource_config=rc,
            cron=CronExpression(expression="0 * * * *"),
        )
        assert ev.run_id == JobRunId(value="r1")
        assert ev.job_id == JobId(value="j1")
        assert ev.trigger_type == TriggerType.MANUAL
        assert ev.job_type == JobType.EXPIRE_SNAPSHOTS
        assert ev.table_ref == TableReference(catalog="cat", table="tbl")
        assert ev.job_config == {"retain_last": 5}
        assert ev.resource_config == rc
        assert ev.cron == CronExpression(expression="0 * * * *")

    def test_has_occurred_at(self):
        ev = JobRunCreated(
            run_id=JobRunId(value="r1"),
            job_id=JobId(value="j1"),
            trigger_type=TriggerType.SCHEDULED,
            job_type=JobType.REWRITE_DATA_FILES,
            table_ref=TableReference(catalog="c", table="t"),
            job_config={},
            resource_config=ResourceConfig(),
            cron=None,
        )
        assert isinstance(ev.occurred_at, datetime)

    def test_cron_none(self):
        ev = JobRunCreated(
            run_id=JobRunId(value="r1"),
            job_id=JobId(value="j1"),
            trigger_type=TriggerType.MANUAL,
            job_type=JobType.EXPIRE_SNAPSHOTS,
            table_ref=TableReference(catalog="c", table="t"),
            job_config={},
            resource_config=ResourceConfig(),
            cron=None,
        )
        assert ev.cron is None


class TestJobRunStarted:
    """Tests for JobRunStarted event."""

    def test_fields(self):
        ts = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
        ev = JobRunStarted(
            run_id=JobRunId(value="r1"),
            job_id=JobId(value="j1"),
            started_at=ts,
        )
        assert ev.started_at == ts


class TestJobRunCompleted:
    """Tests for JobRunCompleted event."""

    def test_fields(self):
        ts = datetime(2026, 4, 25, 13, 0, tzinfo=UTC)
        result = JobRunResult(duration_ms=1500, metadata={"k": "v"})
        ev = JobRunCompleted(
            run_id=JobRunId(value="r1"),
            job_id=JobId(value="j1"),
            finished_at=ts,
            result=result,
        )
        assert ev.finished_at == ts
        assert ev.result == result


class TestJobRunFailed:
    """Tests for JobRunFailed event."""

    def test_fields(self):
        ts = datetime(2026, 4, 25, 14, 0, tzinfo=UTC)
        result = JobRunResult(duration_ms=500, metadata={})
        ev = JobRunFailed(
            run_id=JobRunId(value="r1"),
            job_id=JobId(value="j1"),
            finished_at=ts,
            error="Spark OOM",
            result=result,
        )
        assert ev.finished_at == ts
        assert ev.error == "Spark OOM"
        assert ev.result == result

    def test_result_none(self):
        ts = datetime(2026, 4, 25, 14, 0, tzinfo=UTC)
        ev = JobRunFailed(
            run_id=JobRunId(value="r1"),
            job_id=JobId(value="j1"),
            finished_at=ts,
            error="Connection refused",
            result=None,
        )
        assert ev.result is None


class TestJobRunCancelled:
    """Tests for JobRunCancelled event."""

    def test_fields(self):
        ev = JobRunCancelled(
            run_id=JobRunId(value="r1"),
            job_id=JobId(value="j1"),
        )
        assert ev.run_id == JobRunId(value="r1")
        assert ev.job_id == JobId(value="j1")
