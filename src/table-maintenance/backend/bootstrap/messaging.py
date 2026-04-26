"""Outbox publisher entry point — polls outbox table and dispatches events."""

from __future__ import annotations

import logging
import os
import signal

from adapter.outbound.job_run.sql.job_runs_sql_repo import JobRunsSqlRepo
from adapter.outbound.sql.event_outbox_sql_repo import EventOutboxSqlRepo
from adapter.outbound.sql.metadata import metadata
from application.domain.model.job.events import JobTriggered
from application.service.job_run.job_triggered_handler import JobTriggeredHandler
from application.service.outbox.event_serializer import EventSerializer
from application.service.outbox.publish_events import PublishEventsService
from base.event_dispatcher import EventDispatcher
from adapter.inbound.messaging.outbox.publisher_loop import PublisherLoop
from sqlalchemy import create_engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def build_publisher() -> PublisherLoop:
    """Wire up the outbox publisher with SQL repos and return the loop."""
    database_url = os.environ.get(
        "OUTBOX_DATABASE_URL",
        "sqlite:///scheduler.db",
    )
    interval = int(os.environ.get("OUTBOX_INTERVAL_SECONDS", "5"))

    engine = create_engine(database_url)
    metadata.create_all(engine)

    outbox_repo = EventOutboxSqlRepo(engine)
    job_runs_repo = JobRunsSqlRepo(engine)
    serializer = EventSerializer()

    dispatcher = EventDispatcher()
    dispatcher.register(
        JobTriggered,
        JobTriggeredHandler(job_runs_repo, outbox_repo, serializer),
    )

    service = PublishEventsService(outbox_repo, serializer, dispatcher)
    return PublisherLoop(service, interval_seconds=interval)


def main() -> None:
    """Start the outbox publisher."""
    publisher = build_publisher()
    signal.signal(signal.SIGTERM, lambda *_: publisher.stop())
    signal.signal(signal.SIGINT, lambda *_: publisher.stop())
    logger.info("Starting outbox publisher")
    publisher.start()


if __name__ == "__main__":
    main()
