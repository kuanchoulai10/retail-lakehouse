"""Outbox publisher entry point — polls outbox table and dispatches events."""

from __future__ import annotations

import logging
import signal

from adapter.inbound.messaging.outbox.publisher_loop import PublisherLoop
from adapter.outbound.job_run.k8s.submit_job_run_k8s_gateway import (
    SubmitJobRunK8sGateway,
)
from adapter.outbound.job_run.k8s.k8s_executor_config import K8sExecutorConfig
from adapter.outbound.job_run.sql.job_runs_sql_repo import JobRunsSqlRepo
from adapter.outbound.sql.engine_factory import build_engine
from adapter.outbound.sql.event_outbox_sql_store import EventOutboxSqlStore
from adapter.outbound.sql.metadata import metadata
from application.domain.model.job.events import JobTriggered
from application.domain.model.job_run.events import JobRunCreated
from application.service.handler.job_run_created_handler import JobRunCreatedHandler
from application.service.handler.job_triggered_handler import JobTriggeredHandler
from application.service.job_run.submit_job_run import SubmitJobRunService
from application.service.outbox.event_serializer import EventSerializer
from application.service.outbox.publish_events import PublishEventsService
from base.event_dispatcher import EventDispatcher
from bootstrap.dependencies.k8s import get_k8s_api
from bootstrap.dependencies.settings import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def build_publisher() -> PublisherLoop:
    """Wire up the outbox publisher with SQL repos and return the loop."""
    settings = get_settings()
    engine = build_engine(settings)
    metadata.create_all(engine)

    outbox_repo = EventOutboxSqlStore(engine)
    job_runs_repo = JobRunsSqlRepo(engine)
    serializer = EventSerializer()

    dispatcher = EventDispatcher()
    dispatcher.register(
        JobTriggered,
        JobTriggeredHandler(job_runs_repo, outbox_repo, serializer),
    )

    k8s_api = get_k8s_api()
    k8s_config = K8sExecutorConfig(
        namespace=settings.k8s.namespace,
        image=settings.k8s.image,
        image_pull_policy=settings.k8s.image_pull_policy,
        spark_version=settings.k8s.spark_version,
        service_account=settings.k8s.service_account,
        iceberg_jar=settings.k8s.iceberg_jar,
        iceberg_aws_jar=settings.k8s.iceberg_aws_jar,
    )
    executor = SubmitJobRunK8sGateway(k8s_api, k8s_config)
    submit_service = SubmitJobRunService(executor)
    dispatcher.register(JobRunCreated, JobRunCreatedHandler(submit_service))

    service = PublishEventsService(outbox_repo, serializer, dispatcher)
    return PublisherLoop(service, interval_seconds=settings.messaging.interval_seconds)


def main() -> None:
    """Start the outbox publisher."""
    publisher = build_publisher()
    signal.signal(signal.SIGTERM, lambda *_: publisher.stop())
    signal.signal(signal.SIGINT, lambda *_: publisher.stop())
    logger.info("Starting outbox publisher")
    publisher.start()


if __name__ == "__main__":
    main()
