"""Integration tests: outbox → handlers → executor event chain.

Verifies that PublishEventsService correctly deserializes outbox entries,
dispatches them through real handlers, and the chain terminates at the executor.
All objects are real; only the database is SQLite in-memory.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import create_engine

from adapter.outbound.job.sql.jobs_table import jobs_table as _jobs_table  # noqa: F401
from adapter.outbound.job_run.submit_job_run_in_memory_gateway import (
    SubmitJobRunInMemoryGateway,
)
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
from application.domain.model.job_run.job_run_id import JobRunId
from application.domain.model.job_run.trigger_type import TriggerType
from application.port.outbound.job_run.job_submission import JobSubmission
from application.service.handler.job_run_created_handler import JobRunCreatedHandler
from application.service.handler.job_triggered_handler import JobTriggeredHandler
from application.service.job_run.submit_job_run import SubmitJobRunService
from application.service.outbox.event_serializer import EventSerializer
from application.service.outbox.publish_events import PublishEventsService
from base.event_dispatcher import EventDispatcher

if TYPE_CHECKING:
    from sqlalchemy import Engine


@dataclass
class EventChain:
    """All wired components for the event chain integration test."""

    engine: Engine
    outbox_repo: EventOutboxSqlStore
    job_runs_repo: JobRunsSqlRepo
    serializer: EventSerializer
    dispatcher: EventDispatcher
    executor: SubmitJobRunInMemoryGateway
    publish_service: PublishEventsService


def build_event_chain() -> EventChain:
    """Wire the full outbox event chain with SQLite in-memory."""
    engine = create_engine("sqlite://", echo=False)
    metadata.create_all(engine)

    outbox_repo = EventOutboxSqlStore(engine)
    job_runs_repo = JobRunsSqlRepo(engine)
    serializer = EventSerializer()
    executor = SubmitJobRunInMemoryGateway()

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

    return EventChain(
        engine=engine,
        outbox_repo=outbox_repo,
        job_runs_repo=job_runs_repo,
        serializer=serializer,
        dispatcher=dispatcher,
        executor=executor,
        publish_service=publish_service,
    )


def _make_job_triggered_entry(serializer: EventSerializer) -> list:
    """Create a serialized JobTriggered outbox entry list."""
    event = JobTriggered(
        job_id=JobId(value="job-1"),
        trigger_type=TriggerType.SCHEDULED,
        job_type=JobType.EXPIRE_SNAPSHOTS,
        table_ref=TableReference(catalog="retail", table="inventory.orders"),
        job_config={"retain_last": 5},
        resource_config=ResourceConfig(
            driver_memory="2g", executor_memory="4g", executor_instances=2
        ),
        cron=CronExpression(expression="0 2 * * *"),
    )
    return serializer.to_outbox_entries(
        events=[event], aggregate_type="Job", aggregate_id="job-1"
    )


def _make_job_run_created_entry(serializer: EventSerializer) -> list:
    """Create a serialized JobRunCreated outbox entry list."""
    event = JobRunCreated(
        run_id=JobRunId(value="job-1-abc123"),
        job_id=JobId(value="job-1"),
        trigger_type=TriggerType.SCHEDULED,
        job_type=JobType.EXPIRE_SNAPSHOTS,
        table_ref=TableReference(catalog="retail", table="inventory.orders"),
        job_config={"retain_last": 5},
        resource_config=ResourceConfig(
            driver_memory="2g", executor_memory="4g", executor_instances=2
        ),
        cron=CronExpression(expression="0 2 * * *"),
    )
    return serializer.to_outbox_entries(
        events=[event], aggregate_type="JobRun", aggregate_id="job-1-abc123"
    )


def test_job_triggered_flows_to_pending_job_run():
    """Verify: JobTriggered outbox entry → handler → PENDING JobRun + JobRunCreated in outbox."""
    chain = build_event_chain()

    # Seed a JobTriggered entry in the outbox
    entries = _make_job_triggered_entry(chain.serializer)
    chain.outbox_repo.save(entries)

    # One publish tick
    result = chain.publish_service.execute()
    assert result.published_count == 1

    # JobRun should exist in DB
    all_runs = chain.job_runs_repo.list_all()
    assert len(all_runs) == 1
    assert all_runs[0].job_id == JobId(value="job-1")
    assert all_runs[0].status == JobRunStatus.PENDING

    # A new JobRunCreated entry should be in the outbox (unpublished)
    unpublished = chain.outbox_repo.fetch_unpublished()
    assert len(unpublished) == 1
    assert unpublished[0].event_type == "JobRunCreated"


def test_job_run_created_flows_to_executor_submit():
    """Verify: JobRunCreated outbox entry → handler → executor.submit() with correct fields."""
    chain = build_event_chain()

    # Seed a JobRunCreated entry in the outbox
    entries = _make_job_run_created_entry(chain.serializer)
    chain.outbox_repo.save(entries)

    # One publish tick
    result = chain.publish_service.execute()
    assert result.published_count == 1

    # Executor should have received a submission
    assert len(chain.executor.submitted) == 1
    sub = chain.executor.submitted[0]
    assert isinstance(sub, JobSubmission)
    assert sub.job_id == "job-1"
    assert sub.run_id == "job-1-abc123"
    assert sub.job_type == "expire_snapshots"
    assert sub.catalog == "retail"
    assert sub.table == "inventory.orders"
    assert sub.job_config == {"retain_last": 5}
    assert sub.driver_memory == "2g"
    assert sub.executor_memory == "4g"
    assert sub.executor_instances == 2
    assert sub.cron_expression == "0 2 * * *"


def test_two_ticks_complete_full_chain():
    """Verify: JobTriggered → tick 1 → JobRunCreated → tick 2 → executor receives submission."""
    chain = build_event_chain()

    # Seed a JobTriggered entry
    entries = _make_job_triggered_entry(chain.serializer)
    chain.outbox_repo.save(entries)

    # Tick 1: JobTriggered → handler → creates JobRun + JobRunCreated
    result1 = chain.publish_service.execute()
    assert result1.published_count == 1
    assert len(chain.executor.submitted) == 0  # not yet

    # Tick 2: JobRunCreated → handler → executor.submit()
    result2 = chain.publish_service.execute()
    assert result2.published_count == 1
    assert len(chain.executor.submitted) == 1

    # Verify the submission carries the original Job data
    sub = chain.executor.submitted[0]
    assert sub.job_type == "expire_snapshots"
    assert sub.catalog == "retail"
    assert sub.driver_memory == "2g"
    assert sub.executor_instances == 2
    assert sub.cron_expression == "0 2 * * *"

    # No more unpublished entries
    assert chain.outbox_repo.fetch_unpublished() == []
