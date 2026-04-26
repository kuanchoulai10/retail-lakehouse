"""Scheduler entry point — polls DB and writes trigger events to outbox."""

from __future__ import annotations

import logging
import signal
from datetime import UTC, datetime

from adapter.inbound.scheduler.scheduler_loop import SchedulerLoop
from adapter.outbound.job.sql.jobs_sql_repo import JobsSqlRepo
from adapter.outbound.job_run.sql.job_runs_sql_repo import JobRunsSqlRepo
from adapter.outbound.sql.engine_factory import build_engine
from adapter.outbound.sql.event_outbox_sql_store import EventOutboxSqlStore
from adapter.outbound.sql.metadata import metadata
from application.service.outbox.event_serializer import EventSerializer
from application.service.scheduling.schedule_jobs import ScheduleJobsService
from bootstrap.dependencies.settings import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def build_scheduler() -> SchedulerLoop:
    """Wire up the scheduler with SQL repos and return the loop."""
    settings = get_settings()
    engine = build_engine(settings)
    metadata.create_all(engine)

    jobs_repo = JobsSqlRepo(engine)
    job_runs_repo = JobRunsSqlRepo(engine)
    outbox_repo = EventOutboxSqlStore(engine)
    serializer = EventSerializer()

    service = ScheduleJobsService(
        jobs_repo,
        job_runs_repo,
        clock=lambda: datetime.now(UTC),
        outbox_repo=outbox_repo,
        serializer=serializer,
    )
    return SchedulerLoop(service, interval_seconds=settings.scheduler.interval_seconds)


def main() -> None:
    """Start the scheduler."""
    scheduler = build_scheduler()
    signal.signal(signal.SIGTERM, lambda *_: scheduler.stop())
    signal.signal(signal.SIGINT, lambda *_: scheduler.stop())
    logger.info("Starting table-maintenance scheduler")
    scheduler.start()


if __name__ == "__main__":
    main()
