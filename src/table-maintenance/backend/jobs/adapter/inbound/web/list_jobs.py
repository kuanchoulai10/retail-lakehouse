from fastapi import APIRouter, Depends

from jobs.adapter.inbound.web.deps import get_repo
from jobs.adapter.inbound.web.dto import JobApiResponse
from jobs.application.port.outbound.jobs_repo import BaseJobsRepo

router = APIRouter()


@router.get("/jobs", response_model=list[JobApiResponse])
def list_jobs(repo: BaseJobsRepo = Depends(get_repo)):
    return [
        JobApiResponse(
            id=job.id.value,
            job_type=job.job_type.value,
            status=job.status.value,
            created_at=job.created_at,
        )
        for job in repo.list_all()
    ]
