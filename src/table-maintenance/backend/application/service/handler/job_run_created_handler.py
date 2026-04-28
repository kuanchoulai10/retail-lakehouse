"""Define the handler for JobRunCreated events."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.port.inbound.job_run.submit_job_run import SubmitJobRunUseCaseInput
from base.event_handler import EventHandler

if TYPE_CHECKING:
    from application.domain.model.job_run.events import JobRunCreated
    from application.port.inbound.job_run.submit_job_run import SubmitJobRunUseCase


class JobRunCreatedHandler(EventHandler["JobRunCreated"]):
    """Handle JobRunCreated by delegating to the SubmitJobRun use case.

    Maps the enriched event data into a SubmitJobRunUseCaseInput and delegates
    to the injected use case for execution.
    """

    def __init__(self, use_case: SubmitJobRunUseCase) -> None:
        """Initialize with the submit job run use case."""
        self._use_case = use_case

    def handle(self, event: JobRunCreated) -> None:
        """Map event to SubmitJobRunUseCaseInput and call use case."""
        self._use_case.execute(
            SubmitJobRunUseCaseInput(
                run_id=event.run_id.value,
                job_id=event.job_id.value,
                job_type=event.job_type.value,
                catalog=event.table_ref.catalog,
                table=event.table_ref.table,
                job_config=event.job_config,
                driver_memory=event.resource_config.driver_memory,
                executor_memory=event.resource_config.executor_memory,
                executor_instances=event.resource_config.executor_instances,
                cron_expression=event.cron.expression if event.cron else None,
            )
        )
