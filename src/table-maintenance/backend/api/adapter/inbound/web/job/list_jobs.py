"""Define the GET /jobs endpoint."""

from __future__ import annotations

from dependencies.use_cases import get_list_jobs_use_case
from fastapi import APIRouter, Depends

from api.adapter.inbound.web.job.dto import JobApiResponse
from application.port.inbound import ListJobsInput, ListJobsUseCase

router = APIRouter()


@router.get("/jobs", response_model=list[JobApiResponse])
def list_jobs(
    use_case: ListJobsUseCase = Depends(get_list_jobs_use_case),
):
    """Return all jobs."""
    result = use_case.execute(ListJobsInput())
    return [
        JobApiResponse(
            id=item.id,
            job_type=item.job_type,
            status=item.status,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        for item in result.jobs
    ]
