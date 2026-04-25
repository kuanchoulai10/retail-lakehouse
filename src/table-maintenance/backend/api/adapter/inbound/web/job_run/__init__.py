"""JobRun REST API endpoints."""

from fastapi import APIRouter

from api.adapter.inbound.web.job_run.create_job_run import router as create_run_router
from api.adapter.inbound.web.job_run.get_job_run import router as get_run_router
from api.adapter.inbound.web.job_run.list_job_runs import router as list_runs_router

router = APIRouter(tags=["job-runs"])
router.include_router(create_run_router)
router.include_router(list_runs_router)
router.include_router(get_run_router)
