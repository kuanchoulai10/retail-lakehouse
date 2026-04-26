"""FastAPI web adapter."""

from fastapi import APIRouter

from adapter.inbound.web.catalog import router as catalog_router
from adapter.inbound.web.job import router as job_router
from adapter.inbound.web.job_run import router as job_run_router

router = APIRouter(prefix="/v1")
router.include_router(job_router)
router.include_router(job_run_router)
router.include_router(catalog_router)
