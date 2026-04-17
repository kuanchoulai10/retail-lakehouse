from __future__ import annotations

from base.use_case import UseCase

from application.port.inbound.job_run.create_job_run.input import CreateJobRunInput
from application.port.inbound.job_run.create_job_run.output import CreateJobRunOutput


class CreateJobRunUseCase(UseCase[CreateJobRunInput, CreateJobRunOutput]):
    """Trigger a new execution of a Job, producing a JobRun."""
