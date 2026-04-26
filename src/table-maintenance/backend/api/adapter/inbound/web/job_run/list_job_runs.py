"""Define the GET /jobs/{name}/runs endpoint."""

from __future__ import annotations

from dependencies.use_cases import get_list_job_runs_use_case
from fastapi import APIRouter, Depends

from api.adapter.inbound.web.job_run.dto import JobRunApiResponse
from core.application.port.inbound import ListJobRunsInput, ListJobRunsUseCase

router = APIRouter()


@router.get("/jobs/{name}/runs", response_model=list[JobRunApiResponse])
def list_job_runs(
    name: str,
    use_case: ListJobRunsUseCase = Depends(get_list_job_runs_use_case),
):
    """Return all runs for the specified job."""
    result = use_case.execute(ListJobRunsInput(job_id=name))
    return [
        JobRunApiResponse(
            run_id=r.run_id,
            job_id=r.job_id,
            status=r.status,
            trigger_type=r.trigger_type,
            started_at=r.started_at,
            finished_at=r.finished_at,
        )
        for r in result.runs
    ]
