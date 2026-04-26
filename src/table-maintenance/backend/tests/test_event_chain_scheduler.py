"""Integration tests: scheduler → outbox → two hops → executor.

Verifies the complete event chain from ScheduleJobsService through
the outbox pattern to the executor, using real objects with SQLite in-memory.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import create_engine

from adapter.outbound.job.sql.jobs_sql_repo import JobsSqlRepo
from adapter.outbound.job_run.job_run_in_memory_executor import JobRunInMemoryExecutor
from adapter.outbound.job_run.sql.job_runs_sql_repo import JobRunsSqlRepo
from adapter.outbound.sql.event_outbox_sql_repo import EventOutboxSqlRepo
from adapter.outbound.sql.metadata import metadata
from application.domain.model.job import (
    CronExpression,
    Job,
    JobId,
    JobStatus,
    JobType,
    ResourceConfig,
    TableReference,
)
from application.domain.model.job_run import JobRun, JobRunId, JobRunStatus
from application.domain.model.job_run.events import JobRunCreated
from application.service.job_run.job_run_created_handler import JobRunCreatedHandler
from application.service.job_run.job_triggered_handler import JobTriggeredHandler
from application.service.outbox.event_serializer import EventSerializer
from application.service.outbox.publish_events import PublishEventsService
from application.service.scheduling.schedule_jobs import ScheduleJobsService
from application.domain.model.job.events import JobTriggered
from base.event_dispatcher import EventDispatcher


def _build_full_chain():
    """Wire scheduler + publish chain with SQLite in-memory. Returns all components."""
    engine = create_engine("sqlite://", echo=False)
    metadata.create_all(engine)

    jobs_repo = JobsSqlRepo(engine)
    job_runs_repo = JobRunsSqlRepo(engine)
    outbox_repo = EventOutboxSqlRepo(engine)
    serializer = EventSerializer()
    executor = JobRunInMemoryExecutor()

    dispatcher = EventDispatcher()
    dispatcher.register(
        JobTriggered,
        JobTriggeredHandler(job_runs_repo, outbox_repo, serializer),
    )
    dispatcher.register(
        JobRunCreated,
        JobRunCreatedHandler(executor),
    )

    publish_service = PublishEventsService(outbox_repo, serializer, dispatcher)

    now = datetime(2026, 4, 26, 12, 0, 0, tzinfo=UTC)
    schedule_service = ScheduleJobsService(
        jobs_repo,
        job_runs_repo,
        clock=lambda: now,
        outbox_repo=outbox_repo,
        serializer=serializer,
    )

    return {
        "engine": engine,
        "jobs_repo": jobs_repo,
        "job_runs_repo": job_runs_repo,
        "outbox_repo": outbox_repo,
        "executor": executor,
        "publish_service": publish_service,
        "schedule_service": schedule_service,
    }


def _create_due_job(jobs_repo, **overrides):
    """Insert a due Job into the repo and return it."""
    defaults = {
        "id": JobId(value="sched-job-1"),
        "job_type": JobType.EXPIRE_SNAPSHOTS,
        "created_at": datetime(2026, 4, 20, tzinfo=UTC),
        "updated_at": datetime(2026, 4, 20, tzinfo=UTC),
        "table_ref": TableReference(catalog="retail", table="inventory.orders"),
        "job_config": {"retain_last": 5},
        "cron": CronExpression(expression="0 2 * * *"),
        "status": JobStatus.ACTIVE,
        "next_run_at": datetime(
            2026, 4, 26, 2, 0, 0, tzinfo=UTC
        ),  # in the past relative to clock
        "max_active_runs": 1,
        "resource_config": ResourceConfig(),
    }
    defaults.update(overrides)
    job = Job(**defaults)
    return jobs_repo.create(job)


def test_scheduler_tick_triggers_full_chain():
    """Verify: scheduler tick → outbox → two publish ticks → executor receives correct submission."""
    c = _build_full_chain()

    _create_due_job(c["jobs_repo"])

    # Scheduler tick: finds due job, writes JobTriggered to outbox
    sched_result = c["schedule_service"].execute()
    assert sched_result.triggered_count == 1

    # Tick 1: JobTriggered → JobRun + JobRunCreated
    r1 = c["publish_service"].execute()
    assert r1.published_count == 1

    # Tick 2: JobRunCreated → executor.submit()
    r2 = c["publish_service"].execute()
    assert r2.published_count == 1

    # Verify executor received correct data
    assert len(c["executor"].submitted) == 1
    sub = c["executor"].submitted[0]
    assert sub.job_type == "expire_snapshots"
    assert sub.catalog == "retail"
    assert sub.table == "inventory.orders"
    assert sub.job_config == {"retain_last": 5}
    assert sub.cron_expression == "0 2 * * *"


def test_scheduler_with_custom_resource_config():
    """Verify: per-job ResourceConfig flows through the full chain to executor."""
    c = _build_full_chain()

    rc = ResourceConfig(driver_memory="4g", executor_memory="8g", executor_instances=3)
    _create_due_job(c["jobs_repo"], resource_config=rc)

    c["schedule_service"].execute()
    c["publish_service"].execute()  # tick 1
    c["publish_service"].execute()  # tick 2

    sub = c["executor"].submitted[0]
    assert sub.driver_memory == "4g"
    assert sub.executor_memory == "8g"
    assert sub.executor_instances == 3


def test_scheduler_skips_paused_job():
    """Verify: paused Job is not triggered, outbox stays empty."""
    c = _build_full_chain()

    _create_due_job(c["jobs_repo"], status=JobStatus.PAUSED)

    result = c["schedule_service"].execute()
    assert result.triggered_count == 0

    assert c["outbox_repo"].fetch_unpublished() == []
    assert len(c["executor"].submitted) == 0


def test_scheduler_respects_max_active_runs():
    """Verify: Job at max active runs is not triggered."""
    c = _build_full_chain()

    _create_due_job(c["jobs_repo"], max_active_runs=1)

    # Pre-insert a PENDING JobRun for this job
    run = JobRun(
        id=JobRunId(value="existing-run"),
        job_id=JobId(value="sched-job-1"),
        status=JobRunStatus.PENDING,
        started_at=datetime(2026, 4, 26, 1, 0, tzinfo=UTC),
    )
    c["job_runs_repo"].create(run)

    result = c["schedule_service"].execute()
    assert result.triggered_count == 0
