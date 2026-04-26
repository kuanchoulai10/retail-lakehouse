"""Tests for outbox idempotency and replay behavior.

Verifies that duplicate events produce distinct results and that
published entries are not re-dispatched.
"""

from __future__ import annotations

from sqlalchemy import create_engine

from adapter.outbound.job.sql.jobs_table import jobs_table as _jobs_table  # noqa: F401
from adapter.outbound.job_run.job_run_in_memory_executor import JobRunInMemoryExecutor
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
from application.domain.model.job_run.events import JobRunCreated
from application.domain.model.job_run.trigger_type import TriggerType
from application.service.handler.job_run_created_handler import JobRunCreatedHandler
from application.service.handler.job_triggered_handler import JobTriggeredHandler
from application.service.job_run.submit_job_run import SubmitJobRunService
from application.service.outbox.event_serializer import EventSerializer
from application.service.outbox.publish_events import PublishEventsService
from base.event_dispatcher import EventDispatcher


def _build_chain():
    engine = create_engine("sqlite://", echo=False)
    metadata.create_all(engine)

    outbox_repo = EventOutboxSqlStore(engine)
    job_runs_repo = JobRunsSqlRepo(engine)
    serializer = EventSerializer()
    executor = JobRunInMemoryExecutor()

    dispatcher = EventDispatcher()
    dispatcher.register(
        JobTriggered,
        JobTriggeredHandler(job_runs_repo, outbox_repo, serializer),
    )
    dispatcher.register(
        JobRunCreated,
        JobRunCreatedHandler(SubmitJobRunService(executor)),
    )

    publish_service = PublishEventsService(outbox_repo, serializer, dispatcher)

    return {
        "outbox_repo": outbox_repo,
        "job_runs_repo": job_runs_repo,
        "serializer": serializer,
        "executor": executor,
        "publish_service": publish_service,
    }


def _make_job_triggered_entries(serializer, count=1):
    """Create multiple JobTriggered outbox entries for the same Job."""
    event = JobTriggered(
        job_id=JobId(value="job-1"),
        trigger_type=TriggerType.SCHEDULED,
        job_type=JobType.EXPIRE_SNAPSHOTS,
        table_ref=TableReference(catalog="retail", table="orders"),
        job_config={},
        resource_config=ResourceConfig(),
        cron=CronExpression(expression="0 2 * * *"),
    )
    all_entries = []
    for _ in range(count):
        all_entries.extend(
            serializer.to_outbox_entries(
                events=[event], aggregate_type="Job", aggregate_id="job-1"
            )
        )
    return all_entries


def test_duplicate_job_triggered_creates_two_job_runs():
    """Verify two JobTriggered entries for the same Job create two distinct JobRuns."""
    c = _build_chain()

    entries = _make_job_triggered_entries(c["serializer"], count=2)
    c["outbox_repo"].save(entries)

    # Process both JobTriggered entries
    c["publish_service"].execute()

    runs = c["job_runs_repo"].list_all()
    assert len(runs) == 2
    # IDs should differ (random hex suffix)
    assert runs[0].id != runs[1].id
    # Both linked to the same Job
    assert runs[0].job_id == runs[1].job_id == JobId(value="job-1")


def test_published_entries_not_re_dispatched():
    """Verify that published entries are not picked up on the next tick."""
    c = _build_chain()

    entries = _make_job_triggered_entries(c["serializer"], count=1)
    c["outbox_repo"].save(entries)

    # Tick 1: processes and marks published
    r1 = c["publish_service"].execute()
    assert r1.published_count == 1

    # Tick 2: nothing new to publish (JobRunCreated is there from tick 1)
    r2 = c["publish_service"].execute()
    assert r2.published_count == 1  # the JobRunCreated from tick 1

    # Tick 3: everything published now
    r3 = c["publish_service"].execute()
    assert r3.published_count == 0

    # Executor received exactly one submission (from the JobRunCreated)
    assert len(c["executor"].submitted) == 1
