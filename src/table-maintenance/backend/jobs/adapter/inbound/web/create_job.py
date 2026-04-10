from fastapi import APIRouter, Depends

from jobs.adapter.inbound.web.deps import get_repo
from jobs.adapter.inbound.web.dto import JobApiRequest, JobApiResponse
from jobs.application.port.outbound.jobs_repo import BaseJobsRepo

router = APIRouter()


@router.post("/jobs", response_model=JobApiResponse, status_code=201)
def create_job(request: JobApiRequest, repo: BaseJobsRepo = Depends(get_repo)):
    job = repo.create(request)
    return JobApiResponse(
        id=job.id.value,
        job_type=job.job_type.value,
        status=job.status.value,
        created_at=job.created_at,
    )
