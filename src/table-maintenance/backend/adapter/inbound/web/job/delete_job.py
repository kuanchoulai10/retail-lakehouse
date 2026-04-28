"""Define the DELETE /jobs/{name} endpoint (archives the job)."""

from __future__ import annotations

from bootstrap.dependencies.use_cases import get_update_job_use_case
from fastapi import APIRouter, Depends, HTTPException, Response

from application.exceptions import JobNotFoundError
from application.port.inbound import UpdateJobUseCaseInput, UpdateJobUseCase

router = APIRouter()


@router.delete("/jobs/{name}", status_code=204, response_class=Response)
def delete_job(
    name: str,
    use_case: UpdateJobUseCase = Depends(get_update_job_use_case),
):
    """Archive a job by its name (soft delete)."""
    try:
        use_case.execute(UpdateJobUseCaseInput(job_id=name, status="archived"))
    except JobNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
