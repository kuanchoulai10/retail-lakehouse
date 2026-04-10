from fastapi import APIRouter, Depends, HTTPException

from jobs.adapter.inbound.web.deps import get_repo
from jobs.adapter.inbound.web.dto import JobResponse
from jobs.application.port.outbound.jobs_repo import BaseJobsRepo
from jobs.domain.exceptions import JobNotFoundError

router = APIRouter()


@router.get("/jobs/{name}", response_model=JobResponse)
def get_job(name: str, repo: BaseJobsRepo = Depends(get_repo)):
    try:
        job = repo.get(name)
        return JobResponse.from_domain(job)
    except JobNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
