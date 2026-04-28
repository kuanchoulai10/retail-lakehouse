"""Define the GET /runs/{run_id} endpoint."""

from __future__ import annotations

from bootstrap.dependencies.use_cases import get_get_job_run_use_case
from fastapi import APIRouter, Depends, HTTPException

from adapter.inbound.web.job_run.dto import JobRunApiResponse
from application.exceptions import JobRunNotFoundError
from application.port.inbound import GetJobRunInput, GetJobRunUseCase

router = APIRouter()


@router.get("/runs/{run_id}", response_model=JobRunApiResponse)
def get_job_run(
    run_id: str,
    use_case: GetJobRunUseCase = Depends(get_get_job_run_use_case),
):
    """Retrieve a job run by its identifier."""
    try:
        result = use_case.execute(GetJobRunInput(run_id=run_id))
    except JobRunNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return JobRunApiResponse(
        run_id=result.run_id,
        job_id=result.job_id,
        status=result.status,
        trigger_type=result.trigger_type,
        started_at=result.started_at,
        finished_at=result.finished_at,
        error=result.error,
        result_duration_ms=result.result_duration_ms,
        result_metadata=result.result_metadata,
    )
