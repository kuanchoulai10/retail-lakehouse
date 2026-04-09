from fastapi import APIRouter, Depends, HTTPException
from models.job_response import JobResponse
from repos.base_jobs_repo import BaseJobsRepo
from repos.exceptions import JobNotFoundError

from api.jobs._deps import get_repo

router = APIRouter()


@router.get("/jobs/{name}", response_model=JobResponse)
def get_job(name: str, repo: BaseJobsRepo = Depends(get_repo)):
    try:
        return repo.get(name)
    except JobNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
