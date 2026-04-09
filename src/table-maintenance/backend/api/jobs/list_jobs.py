from fastapi import APIRouter, Depends
from models.job_response import JobResponse
from repos.base import JobsRepo

from api.jobs._deps import get_repo

router = APIRouter()


@router.get("/jobs", response_model=list[JobResponse])
def list_jobs(repo: JobsRepo = Depends(get_repo)):
    return repo.list_all()
