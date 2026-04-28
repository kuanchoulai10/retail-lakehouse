"""POST /runs/{run_id}/fail endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from adapter.inbound.web.job_run.dto import (
    FailJobRunRequest,
    JobRunCallbackResponse,
)
from application.exceptions import JobRunNotFoundError
from application.port.inbound.job_run.fail_job_run import (
    FailJobRunInput,
    FailJobRunUseCase,
)
from bootstrap.dependencies.use_cases import get_fail_job_run_use_case

router = APIRouter()


@router.post("/runs/{run_id}/fail", response_model=JobRunCallbackResponse)
def fail_job_run(
    run_id: str,
    body: FailJobRunRequest,
    use_case: FailJobRunUseCase = Depends(get_fail_job_run_use_case),
) -> JobRunCallbackResponse:
    """Mark a job run as failed with error details."""
    try:
        result = use_case.execute(
            FailJobRunInput(
                run_id=run_id,
                error=body.error,
                duration_ms=body.duration_ms,
                metadata=body.metadata,
            )
        )
    except JobRunNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return JobRunCallbackResponse(
        run_id=result.run_id,
        status=result.status,
        finished_at=result.finished_at,
    )
