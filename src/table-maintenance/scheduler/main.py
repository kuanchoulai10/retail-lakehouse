"""Scheduler entry point — polls DB and creates JobRuns for due jobs."""

from __future__ import annotations

import logging
import os
import signal
from datetime import UTC, datetime

from adapter.outbound.job.sql.jobs_sql_repo import JobsSqlRepo
from adapter.outbound.job_run.sql.job_runs_sql_repo import JobRunsSqlRepo
from adapter.outbound.sql.metadata import metadata
from application.domain.service.schedule_jobs import ScheduleJobsService
from scheduler_loop import SchedulerLoop
from sqlalchemy import create_engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def build_scheduler() -> SchedulerLoop:
    """Wire up the scheduler with SQL repos and return the loop."""
    database_url = os.environ.get(
        "SCHEDULER_DATABASE_URL",
        "sqlite:///scheduler.db",
    )
    interval = int(os.environ.get("SCHEDULER_INTERVAL_SECONDS", "30"))

    engine = create_engine(database_url)
    metadata.create_all(engine)

    jobs_repo = JobsSqlRepo(engine)
    job_runs_repo = JobRunsSqlRepo(engine)
    service = ScheduleJobsService(
        jobs_repo,
        job_runs_repo,
        clock=lambda: datetime.now(UTC),
    )
    return SchedulerLoop(service, interval_seconds=interval)


def main() -> None:
    """Start the scheduler."""
    scheduler = build_scheduler()
    signal.signal(signal.SIGTERM, lambda *_: scheduler.stop())
    signal.signal(signal.SIGINT, lambda *_: scheduler.stop())
    logger.info("Starting table-maintenance scheduler")
    scheduler.start()


if __name__ == "__main__":
    main()
