from __future__ import annotations

from typing import TYPE_CHECKING

from jobs.application.port.inbound import CreateJobInput, CreateJobOutput, CreateJobUseCase

if TYPE_CHECKING:
    from jobs.adapter.inbound.web.dto import JobApiRequest
    from jobs.application.port.outbound.jobs_repo import BaseJobsRepo


def _to_api_request(input_: CreateJobInput) -> JobApiRequest:
    from jobs.adapter.inbound.web.dto import JobApiRequest

    return JobApiRequest(
        job_type=input_.job_type,
        catalog=input_.catalog,
        spark_conf=input_.spark_conf,
        expire_snapshots=input_.expire_snapshots,
        remove_orphan_files=input_.remove_orphan_files,
        rewrite_data_files=input_.rewrite_data_files,
        rewrite_manifests=input_.rewrite_manifests,
        driver_memory=input_.driver_memory,
        executor_memory=input_.executor_memory,
        executor_instances=input_.executor_instances,
        cron=input_.cron,
    )


class CreateJobService(CreateJobUseCase):
    """Implements CreateJobUseCase by delegating to the jobs repository."""

    def __init__(self, repo: BaseJobsRepo) -> None:
        self._repo = repo

    def execute(self, request: CreateJobInput) -> CreateJobOutput:
        job = self._repo.create(_to_api_request(request))
        return CreateJobOutput(
            id=job.id.value,
            job_type=job.job_type.value,
            status=job.status.value,
            created_at=job.created_at,
        )
