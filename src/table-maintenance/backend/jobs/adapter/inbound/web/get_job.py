from fastapi import APIRouter, Depends, HTTPException

from jobs.adapter.inbound.web.dto import JobApiResponse
from jobs.application.exceptions import JobNotFoundError
from jobs.application.port.inbound import GetJobInput, GetJobUseCase

router = APIRouter()


def _get_use_case() -> GetJobUseCase:
    raise NotImplementedError("Dependency not wired — call app.dependency_overrides")


@router.get("/jobs/{name}", response_model=JobApiResponse)
def get_job(name: str, use_case: GetJobUseCase = Depends(_get_use_case)):
    try:
        result = use_case.execute(GetJobInput(job_id=name))
        return JobApiResponse(
            id=result.id,
            job_type=result.job_type,
            status=result.status,
            created_at=result.created_at,
        )
    except JobNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
