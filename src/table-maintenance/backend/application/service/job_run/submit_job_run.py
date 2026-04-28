"""Define the SubmitJobRunService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from application.domain.model.job_run import JobRunId
from application.port.inbound.job_run.submit_job_run import (
    SubmitJobRunUseCaseInput,
    SubmitJobRunUseCase,
)
from application.port.outbound.job_run.submit_job_run.input import (
    SubmitJobRunGatewayInput,
)

if TYPE_CHECKING:
    from application.port.outbound.job_run.job_runs_repo import JobRunsRepo
    from application.port.outbound.job_run.submit_job_run.gateway import (
        SubmitJobRunGateway,
    )


class SubmitJobRunService(SubmitJobRunUseCase):
    """Map a SubmitJobRunUseCaseInput to a SubmitJobRunGatewayInput and delegate to the executor."""

    def __init__(self, executor: SubmitJobRunGateway, repo: JobRunsRepo) -> None:
        """Initialize with the job run executor and repository."""
        self._executor = executor
        self._repo = repo

    def execute(self, request: SubmitJobRunUseCaseInput) -> None:
        """Build a SubmitJobRunGatewayInput from the input, submit it, and mark as RUNNING."""
        submission = SubmitJobRunGatewayInput(
            run_id=request.run_id,
            job_id=request.job_id,
            job_type=request.job_type,
            catalog=request.catalog,
            table=request.table,
            job_config=request.job_config,
            driver_memory=request.driver_memory,
            executor_memory=request.executor_memory,
            executor_instances=request.executor_instances,
            cron_expression=request.cron_expression,
        )
        self._executor.submit(submission)
        run = self._repo.get(JobRunId(value=request.run_id))
        run.mark_running(started_at=datetime.now(UTC))
        self._repo.save(run)
