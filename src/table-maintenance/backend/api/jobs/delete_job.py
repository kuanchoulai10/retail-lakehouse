from fastapi import APIRouter, Depends, HTTPException, Response
from repos.base import JobNotFoundError, JobsRepo

from api.jobs._deps import get_repo

router = APIRouter()


@router.delete("/jobs/{name}", status_code=204, response_class=Response)
def delete_job(name: str, repo: JobsRepo = Depends(get_repo)):
    try:
        repo.delete(name)
    except JobNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
