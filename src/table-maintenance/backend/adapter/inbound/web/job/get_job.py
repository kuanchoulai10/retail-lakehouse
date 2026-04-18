"""Define the GET /jobs/{name} endpoint."""

from __future__ import annotations

from dependencies.use_cases import get_get_job_use_case
from fastapi import APIRouter, Depends, HTTPException

from adapter.inbound.web.job.dto import JobApiResponse
from application.exceptions import JobNotFoundError
from application.port.inbound import GetJobInput, GetJobUseCase

router = APIRouter()


@router.get("/jobs/{name}", response_model=JobApiResponse)
def get_job(
    name: str,
    use_case: GetJobUseCase = Depends(get_get_job_use_case),
):
    """Retrieve a job by its name."""
    try:
        result = use_case.execute(GetJobInput(job_id=name))
        return JobApiResponse(
            id=result.id,
            job_type=result.job_type,
            enabled=result.enabled,
            created_at=result.created_at,
            updated_at=result.updated_at,
        )
    except JobNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
