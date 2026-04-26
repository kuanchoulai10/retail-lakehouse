"""Define the POST /jobs/{name}/runs endpoint."""

from __future__ import annotations

from bootstrap.dependencies.use_cases import get_create_job_run_use_case
from fastapi import APIRouter, Depends, HTTPException

from application.exceptions import JobDisabledError, JobNotFoundError
from application.port.inbound import CreateJobRunInput, CreateJobRunUseCase

router = APIRouter()


@router.post(
    "/jobs/{name}/runs",
    status_code=202,
)
def create_job_run(
    name: str,
    use_case: CreateJobRunUseCase = Depends(get_create_job_run_use_case),
):
    """Trigger a new run for the specified job (async — run created by outbox consumer)."""
    try:
        result = use_case.execute(CreateJobRunInput(job_id=name))
    except JobNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except JobDisabledError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return {"job_id": result.job_id, "accepted": result.accepted}
