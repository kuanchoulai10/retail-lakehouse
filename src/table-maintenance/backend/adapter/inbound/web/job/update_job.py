"""Define the PATCH /jobs/{name} endpoint."""

from __future__ import annotations

from bootstrap.dependencies.use_cases import get_update_job_use_case
from fastapi import APIRouter, Depends, HTTPException

from adapter.inbound.web.job.dto import JobApiResponse, UpdateJobApiRequest
from application.exceptions import JobNotFoundError
from application.port.inbound import UpdateJobInput, UpdateJobUseCase

router = APIRouter()


@router.patch("/jobs/{name}", response_model=JobApiResponse)
def update_job(
    name: str,
    request: UpdateJobApiRequest,
    use_case: UpdateJobUseCase = Depends(get_update_job_use_case),
):
    """Apply partial updates to a job."""
    try:
        result = use_case.execute(
            UpdateJobInput(
                job_id=name,
                status=request.status,
                catalog=request.catalog,
                cron=request.cron,
                job_config=request.job_config,
            )
        )
        return JobApiResponse(
            id=result.id,
            job_type=result.job_type,
            status=result.status,
            created_at=result.created_at,
            updated_at=result.updated_at,
        )
    except JobNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
