from fastapi import APIRouter, Depends, HTTPException

from jobs.adapter.inbound.web.dto import JobResponse
from jobs.application.port.inbound.get_job import GetJobUseCase
from jobs.domain.exceptions import JobNotFoundError

router = APIRouter()


def _get_use_case() -> GetJobUseCase:
    raise NotImplementedError("Dependency not wired — call app.dependency_overrides")


@router.get("/jobs/{name}", response_model=JobResponse)
def get_job(name: str, use_case: GetJobUseCase = Depends(_get_use_case)):
    try:
        job = use_case.execute(name)
        return JobResponse.from_domain(job)
    except JobNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
