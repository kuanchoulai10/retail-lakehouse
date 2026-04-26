"""Define the handler for JobRunCreated events."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.port.outbound.job_run.job_submission import JobSubmission
from base.event_handler import EventHandler

if TYPE_CHECKING:
    from application.domain.model.job_run.events import JobRunCreated
    from application.port.outbound.job_run.job_run_executor import JobRunExecutor


class JobRunCreatedHandler(EventHandler["JobRunCreated"]):
    """Handle JobRunCreated by submitting the job to an external executor.

    Maps the enriched event data into a JobSubmission and delegates
    to the injected JobRunExecutor.
    """

    def __init__(self, executor: JobRunExecutor) -> None:
        """Initialize with the job run executor."""
        self._executor = executor

    def handle(self, event: JobRunCreated) -> None:
        """Map event to JobSubmission and call executor.submit()."""
        submission = JobSubmission(
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
        self._executor.submit(submission)
