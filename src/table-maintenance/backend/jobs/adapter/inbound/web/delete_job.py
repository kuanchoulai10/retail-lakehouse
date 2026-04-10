from fastapi import APIRouter, Depends, HTTPException, Response

from jobs.adapter.inbound.web.deps import get_repo
from jobs.application.port.outbound.jobs_repo import BaseJobsRepo
from jobs.domain.exceptions import JobNotFoundError

router = APIRouter()


@router.delete("/jobs/{name}", status_code=204, response_class=Response)
def delete_job(name: str, repo: BaseJobsRepo = Depends(get_repo)):
    try:
        repo.delete(name)
    except JobNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
