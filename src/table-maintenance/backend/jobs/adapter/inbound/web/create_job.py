from fastapi import APIRouter, Depends

from jobs.adapter.inbound.web.deps import get_repo
from jobs.adapter.inbound.web.dto import JobRequest, JobResponse
from jobs.application.port.outbound.jobs_repo import BaseJobsRepo

router = APIRouter()


@router.post("/jobs", response_model=JobResponse, status_code=201)
def create_job(request: JobRequest, repo: BaseJobsRepo = Depends(get_repo)):
    job = repo.create(request)
    return JobResponse.from_domain(job)
