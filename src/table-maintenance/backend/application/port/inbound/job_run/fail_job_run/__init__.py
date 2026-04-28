"""FailJobRun use case definition."""

from application.port.inbound.job_run.fail_job_run.input import FailJobRunInput
from application.port.inbound.job_run.fail_job_run.output import FailJobRunOutput
from application.port.inbound.job_run.fail_job_run.use_case import FailJobRunUseCase

__all__ = ["FailJobRunInput", "FailJobRunOutput", "FailJobRunUseCase"]
