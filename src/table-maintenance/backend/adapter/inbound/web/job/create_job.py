from __future__ import annotations

from dependencies.use_cases import get_create_job_use_case
from fastapi import APIRouter, Depends

from adapter.inbound.web.job.dto import JobApiRequest, JobApiResponse
from application.port.inbound import CreateJobInput, CreateJobUseCase

router = APIRouter()


@router.post("/jobs", response_model=JobApiResponse, status_code=201)
def create_job(
    request: JobApiRequest,
    use_case: CreateJobUseCase = Depends(get_create_job_use_case),
):
    result = use_case.execute(
        CreateJobInput(
            job_type=request.job_type,
            catalog=request.catalog,
            expire_snapshots=request.expire_snapshots,
            remove_orphan_files=request.remove_orphan_files,
            rewrite_data_files=request.rewrite_data_files,
            rewrite_manifests=request.rewrite_manifests,
            cron=request.cron,
            enabled=request.enabled,
        )
    )
    return JobApiResponse(
        id=result.id,
        job_type=result.job_type,
        enabled=result.enabled,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )
