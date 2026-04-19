"""Define the POST /jobs/{name}/runs endpoint."""

from __future__ import annotations

from dependencies.use_cases import get_create_job_run_use_case
from fastapi import APIRouter, Depends, HTTPException

from adapter.inbound.web.job_run.dto import JobRunApiResponse
from application.exceptions import JobDisabledError, JobNotFoundError
from application.port.inbound import CreateJobRunInput, CreateJobRunUseCase

router = APIRouter()


@router.post(
    "/jobs/{name}/runs",
    response_model=JobRunApiResponse,
    status_code=201,
)
def create_job_run(
    name: str,
    use_case: CreateJobRunUseCase = Depends(get_create_job_run_use_case),
):
    """Trigger a new run for the specified job."""
    try:
        result = use_case.execute(CreateJobRunInput(job_id=name))
    except JobNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except JobDisabledError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return JobRunApiResponse(
        run_id=result.run_id,
        job_id=result.job_id,
        status=result.status,
        started_at=result.started_at,
        finished_at=result.finished_at,
    )
