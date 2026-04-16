from fastapi import APIRouter

from adapter.inbound.web.create_job import router as create_router
from adapter.inbound.web.create_job_run import router as create_run_router
from adapter.inbound.web.delete_job import router as delete_router
from adapter.inbound.web.get_job import router as get_router
from adapter.inbound.web.get_job_run import router as get_run_router
from adapter.inbound.web.list_job_runs import router as list_runs_router
from adapter.inbound.web.list_jobs import router as list_router
from adapter.inbound.web.update_job import router as update_router

router = APIRouter(prefix="/v1", tags=["jobs"])
router.include_router(create_router)
router.include_router(list_router)
router.include_router(get_router)
router.include_router(update_router)
router.include_router(delete_router)
router.include_router(create_run_router)
router.include_router(list_runs_router)
router.include_router(get_run_router)
