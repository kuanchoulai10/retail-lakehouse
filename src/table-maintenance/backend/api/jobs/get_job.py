from fastapi import APIRouter, Depends, HTTPException
from models import JobResponse
from repos import BaseJobsRepo, JobNotFoundError

from api.jobs._deps import get_repo

router = APIRouter()


@router.get("/jobs/{name}", response_model=JobResponse)
def get_job(name: str, repo: BaseJobsRepo = Depends(get_repo)):
    try:
        return repo.get(name)
    except JobNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
