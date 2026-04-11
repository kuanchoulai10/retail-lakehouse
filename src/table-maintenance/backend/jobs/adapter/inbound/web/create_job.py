from fastapi import APIRouter, Depends

from jobs.adapter.inbound.web.dto import JobApiRequest, JobApiResponse
from jobs.application.port.inbound import CreateJobInput, CreateJobUseCase

router = APIRouter()


def _get_use_case() -> CreateJobUseCase:
    raise NotImplementedError("Dependency not wired — call app.dependency_overrides")


@router.post("/jobs", response_model=JobApiResponse, status_code=201)
def create_job(request: JobApiRequest, use_case: CreateJobUseCase = Depends(_get_use_case)):
    result = use_case.execute(
        CreateJobInput(
            job_type=request.job_type,
            catalog=request.catalog,
            spark_conf=request.spark_conf,
            expire_snapshots=request.expire_snapshots,
            remove_orphan_files=request.remove_orphan_files,
            rewrite_data_files=request.rewrite_data_files,
            rewrite_manifests=request.rewrite_manifests,
            driver_memory=request.driver_memory,
            executor_memory=request.executor_memory,
            executor_instances=request.executor_instances,
            cron=request.cron,
        )
    )
    return JobApiResponse(
        id=result.id,
        job_type=result.job_type,
        status=result.status,
        created_at=result.created_at,
    )
