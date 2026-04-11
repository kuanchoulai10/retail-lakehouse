from fastapi import APIRouter, Depends

from jobs.adapter.inbound.web.dto import JobApiResponse
from jobs.application.port.inbound import ListJobsInput, ListJobsUseCase

router = APIRouter()


def _get_use_case() -> ListJobsUseCase:
    raise NotImplementedError("Dependency not wired — call app.dependency_overrides")


@router.get("/jobs", response_model=list[JobApiResponse])
def list_jobs(use_case: ListJobsUseCase = Depends(_get_use_case)):
    result = use_case.execute(ListJobsInput())
    return [
        JobApiResponse(
            id=item.id,
            job_type=item.job_type,
            status=item.status,
            created_at=item.created_at,
        )
        for item in result.jobs
    ]
