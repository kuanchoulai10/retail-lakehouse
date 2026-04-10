from fastapi import APIRouter, Depends
from models import JobResponse
from repos import BaseJobsRepo

from api.jobs._deps import get_repo

router = APIRouter()


@router.get("/jobs", response_model=list[JobResponse])
def list_jobs(repo: BaseJobsRepo = Depends(get_repo)):
    return repo.list_all()
