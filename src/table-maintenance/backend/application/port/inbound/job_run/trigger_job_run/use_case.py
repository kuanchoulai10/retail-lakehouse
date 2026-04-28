"""Define the TriggerJobRunUseCase interface."""

from __future__ import annotations

from base.use_case import UseCase

from application.port.inbound.job_run.trigger_job_run.input import (
    TriggerJobRunUseCaseInput,
)
from application.port.inbound.job_run.trigger_job_run.output import (
    TriggerJobRunUseCaseOutput,
)


class TriggerJobRunUseCase(
    UseCase[TriggerJobRunUseCaseInput, TriggerJobRunUseCaseOutput]
):
    """Trigger a new execution of a Job — returns acceptance, not run details."""
