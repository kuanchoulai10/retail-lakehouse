"""Define the SubmitJobRunService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.port.inbound.job_run.submit_job_run import (
    SubmitJobRunInput,
    SubmitJobRunUseCase,
)
from application.port.outbound.job_run.submit_job_run.input import (
    SubmitJobRunInput as SubmitJobRunGatewayInput,
)

if TYPE_CHECKING:
    from application.port.outbound.job_run.submit_job_run.gateway import (
        SubmitJobRunGateway,
    )


class SubmitJobRunService(SubmitJobRunUseCase):
    """Map a SubmitJobRunInput to a SubmitJobRunGatewayInput and delegate to the executor."""

    def __init__(self, executor: SubmitJobRunGateway) -> None:
        """Initialize with the job run executor."""
        self._executor = executor

    def execute(self, request: SubmitJobRunInput) -> None:
        """Build a SubmitJobRunGatewayInput from the input and submit it."""
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
