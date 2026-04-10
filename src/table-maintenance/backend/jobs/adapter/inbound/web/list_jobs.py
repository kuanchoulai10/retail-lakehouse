from fastapi import APIRouter, Depends

from jobs.adapter.inbound.web.deps import get_repo
from jobs.adapter.inbound.web.dto import JobResponse
from jobs.application.port.outbound.jobs_repo import BaseJobsRepo

router = APIRouter()


@router.get("/jobs", response_model=list[JobResponse])
def list_jobs(repo: BaseJobsRepo = Depends(get_repo)):
    return repo.list_all()
