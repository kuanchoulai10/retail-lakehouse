"""FailJobRun use case definition."""

from application.port.inbound.job_run.fail_job_run.input import FailJobRunUseCaseInput
from application.port.inbound.job_run.fail_job_run.output import FailJobRunUseCaseOutput
from application.port.inbound.job_run.fail_job_run.use_case import FailJobRunUseCase

__all__ = ["FailJobRunUseCaseInput", "FailJobRunUseCaseOutput", "FailJobRunUseCase"]
