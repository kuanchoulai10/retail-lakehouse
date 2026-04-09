from fastapi import APIRouter, Depends
from models.requests import JobRequest
from models.responses import JobResponse
from repos.base import JobsRepo

from api.jobs._deps import get_repo

router = APIRouter()


@router.post("/jobs", response_model=JobResponse, status_code=201)
def create_job(request: JobRequest, repo: JobsRepo = Depends(get_repo)):
    return repo.create(request)
