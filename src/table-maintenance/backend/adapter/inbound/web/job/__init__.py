from fastapi import APIRouter

from adapter.inbound.web.job.create_job import router as create_router
from adapter.inbound.web.job.delete_job import router as delete_router
from adapter.inbound.web.job.get_job import router as get_router
from adapter.inbound.web.job.list_jobs import router as list_router
from adapter.inbound.web.job.update_job import router as update_router

router = APIRouter(tags=["jobs"])
router.include_router(create_router)
router.include_router(list_router)
router.include_router(get_router)
router.include_router(update_router)
router.include_router(delete_router)
