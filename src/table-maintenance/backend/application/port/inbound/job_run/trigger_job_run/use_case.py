"""Define the TriggerJobRunUseCase interface."""

from __future__ import annotations

from base.use_case import UseCase

from application.port.inbound.job_run.trigger_job_run.input import TriggerJobRunInput
from application.port.inbound.job_run.trigger_job_run.output import (
    TriggerJobRunOutput,
)


class TriggerJobRunUseCase(UseCase[TriggerJobRunInput, TriggerJobRunOutput]):
    """Trigger a new execution of a Job — returns acceptance, not run details."""
