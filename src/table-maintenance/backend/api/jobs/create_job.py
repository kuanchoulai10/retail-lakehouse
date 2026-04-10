from fastapi import APIRouter, Depends
from models import JobRequest, JobResponse
from repos import BaseJobsRepo

from api.jobs._deps import get_repo

router = APIRouter()


@router.post("/jobs", response_model=JobResponse, status_code=201)
def create_job(request: JobRequest, repo: BaseJobsRepo = Depends(get_repo)):
    return repo.create(request)
