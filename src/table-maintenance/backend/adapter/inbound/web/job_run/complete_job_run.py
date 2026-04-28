"""POST /runs/{run_id}/complete endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from adapter.inbound.web.job_run.dto import (
    CompleteJobRunRequest,
    JobRunCallbackResponse,
)
from application.exceptions import JobRunNotFoundError
from application.port.inbound.job_run.complete_job_run import (
    CompleteJobRunInput,
    CompleteJobRunUseCase,
)
from bootstrap.dependencies.use_cases import get_complete_job_run_use_case

router = APIRouter()


@router.post("/runs/{run_id}/complete", response_model=JobRunCallbackResponse)
def complete_job_run(
    run_id: str,
    body: CompleteJobRunRequest,
    use_case: CompleteJobRunUseCase = Depends(get_complete_job_run_use_case),
) -> JobRunCallbackResponse:
    """Mark a job run as completed with result metadata."""
    try:
        result = use_case.execute(
            CompleteJobRunInput(
                run_id=run_id,
                duration_ms=body.duration_ms,
                metadata=body.metadata or {},
            )
        )
    except JobRunNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return JobRunCallbackResponse(
        run_id=result.run_id,
        status=result.status,
        finished_at=result.finished_at,
    )
