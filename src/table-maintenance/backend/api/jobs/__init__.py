from fastapi import APIRouter

from api.jobs.create_job import router as create_router
from api.jobs.delete_job import router as delete_router
from api.jobs.get_job import router as get_router
from api.jobs.list_jobs import router as list_router

router = APIRouter(prefix="/v1", tags=["jobs"])
router.include_router(create_router)
router.include_router(list_router)
router.include_router(get_router)
router.include_router(delete_router)
