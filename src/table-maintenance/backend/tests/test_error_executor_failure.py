"""Tests for executor failure behavior in the event chain.

Verifies that when the executor raises, the JobRun created in the first hop
is preserved and outbox entries remain retryable.
"""

from __future__ import annotations

import pytest

from sqlalchemy import create_engine

from adapter.outbound.job.sql.jobs_table import jobs_table as _jobs_table  # noqa: F401
from adapter.outbound.job_run.sql.job_runs_sql_repo import JobRunsSqlRepo
from adapter.outbound.sql.event_outbox_sql_store import EventOutboxSqlStore
from adapter.outbound.sql.metadata import metadata
from application.domain.model.job import (
    CronExpression,
    JobId,
    JobType,
    ResourceConfig,
    TableReference,
)
from application.domain.model.job.events import JobTriggered
from application.domain.model.job_run import JobRunStatus
from application.domain.model.job_run.events import JobRunCreated
from application.port.outbound.job_run.job_run_executor import JobRunExecutor
from application.port.outbound.job_run.job_submission import JobSubmission
from application.service.handler.job_run_created_handler import JobRunCreatedHandler
from application.service.handler.job_triggered_handler import JobTriggeredHandler
from application.service.job_run.submit_job_run import SubmitJobRunService
from application.service.outbox.event_serializer import EventSerializer
from application.service.outbox.publish_events import PublishEventsService
from base.event_dispatcher import EventDispatcher
from application.domain.model.job_run import TriggerType


class FailingExecutor(JobRunExecutor):
    """Executor that always raises to simulate K8s unavailability."""

    def submit(self, submission: JobSubmission) -> None:
        """Raise RuntimeError to simulate failure."""
        raise RuntimeError("K8s unavailable")


def _build_chain_with_failing_executor():
    """Wire event chain with a FailingExecutor for the second hop."""
    engine = create_engine("sqlite://", echo=False)
    metadata.create_all(engine)

    outbox_repo = EventOutboxSqlStore(engine)
    job_runs_repo = JobRunsSqlRepo(engine)
    serializer = EventSerializer()

    dispatcher = EventDispatcher()
    dispatcher.register(
        JobTriggered,
        JobTriggeredHandler(job_runs_repo, outbox_repo, serializer),
    )
    dispatcher.register(
        JobRunCreated,
        JobRunCreatedHandler(SubmitJobRunService(FailingExecutor())),
    )

    publish_service = PublishEventsService(outbox_repo, serializer, dispatcher)

    return {
        "outbox_repo": outbox_repo,
        "job_runs_repo": job_runs_repo,
        "serializer": serializer,
        "publish_service": publish_service,
    }


def _seed_job_triggered(serializer, outbox_repo):
    """Insert a JobTriggered outbox entry."""
    event = JobTriggered(
        job_id=JobId(value="job-1"),
        trigger_type=TriggerType.SCHEDULED,
        job_type=JobType.EXPIRE_SNAPSHOTS,
        table_ref=TableReference(catalog="retail", table="orders"),
        job_config={},
        resource_config=ResourceConfig(),
        cron=CronExpression(expression="0 2 * * *"),
    )
    entries = serializer.to_outbox_entries(
        events=[event], aggregate_type="Job", aggregate_id="job-1"
    )
    outbox_repo.save(entries)


def test_executor_failure_does_not_lose_job_run():
    """Verify: first hop creates JobRun; second hop fails but JobRun is safe in DB."""
    c = _build_chain_with_failing_executor()

    _seed_job_triggered(c["serializer"], c["outbox_repo"])

    # Tick 1: JobTriggered → creates JobRun + JobRunCreated (succeeds)
    c["publish_service"].execute()

    # JobRun should be persisted
    all_runs = c["job_runs_repo"].list_all()
    assert len(all_runs) == 1
    assert all_runs[0].status == JobRunStatus.PENDING

    # Tick 2: JobRunCreated → FailingExecutor raises
    with pytest.raises(RuntimeError, match="K8s unavailable"):
        c["publish_service"].execute()

    # JobRun is still safe in DB
    all_runs_after = c["job_runs_repo"].list_all()
    assert len(all_runs_after) == 1
    assert all_runs_after[0].status == JobRunStatus.PENDING


def test_executor_failure_entry_stays_unpublished():
    """Verify: when executor fails, the outbox entry remains unpublished for retry."""
    c = _build_chain_with_failing_executor()

    _seed_job_triggered(c["serializer"], c["outbox_repo"])

    # Tick 1: processes JobTriggered successfully
    c["publish_service"].execute()

    # Tick 2: fails on JobRunCreated
    with pytest.raises(RuntimeError, match="K8s unavailable"):
        c["publish_service"].execute()

    # The JobRunCreated entry should still be unpublished (retryable)
    unpublished = c["outbox_repo"].fetch_unpublished()
    assert len(unpublished) == 1
    assert unpublished[0].event_type == "JobRunCreated"
