"""Tests for JobTriggeredHandler."""

from unittest.mock import MagicMock

from application.domain.model.job import (
    CronExpression,
    JobId,
    JobType,
    ResourceConfig,
    TableReference,
)
from application.domain.model.job.events import JobTriggered
from application.domain.model.job_run import TriggerType
from application.domain.model.job_run.events import JobRunCreated
from application.service.handler.job_triggered_handler import JobTriggeredHandler


def _make_enriched_event() -> JobTriggered:
    return JobTriggered(
        job_id=JobId(value="j1"),
        trigger_type=TriggerType.SCHEDULED,
        job_type=JobType.EXPIRE_SNAPSHOTS,
        table_ref=TableReference(catalog="retail", table="orders"),
        job_config={"retain_last": 5},
        resource_config=ResourceConfig(
            driver_memory="2g", executor_memory="4g", executor_instances=2
        ),
        cron=CronExpression(expression="0 2 * * *"),
    )


def test_creates_pending_job_run():
    """Verify handler creates a PENDING JobRun and persists it."""
    runs_repo = MagicMock()
    outbox_repo = MagicMock()
    serializer = MagicMock()
    handler = JobTriggeredHandler(runs_repo, outbox_repo, serializer)

    handler.handle(_make_enriched_event())

    runs_repo.create.assert_called_once()


def test_outbox_receives_enriched_job_run_created():
    """Verify the serializer receives a JobRunCreated event with enriched Job info."""
    runs_repo = MagicMock()
    outbox_repo = MagicMock()
    serializer = MagicMock()
    handler = JobTriggeredHandler(runs_repo, outbox_repo, serializer)

    handler.handle(_make_enriched_event())

    serializer.to_outbox_entries.assert_called_once()
    events_passed = serializer.to_outbox_entries.call_args.kwargs["events"]
    assert len(events_passed) == 1
    created_event = events_passed[0]
    assert isinstance(created_event, JobRunCreated)
    assert created_event.job_type == JobType.EXPIRE_SNAPSHOTS
    assert created_event.table_ref == TableReference(catalog="retail", table="orders")
    assert created_event.job_config == {"retain_last": 5}
    assert created_event.resource_config == ResourceConfig(
        driver_memory="2g", executor_memory="4g", executor_instances=2
    )
    assert created_event.cron == CronExpression(expression="0 2 * * *")
