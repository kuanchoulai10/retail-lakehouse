from fastapi import APIRouter

from api.routes.create import router as create_router
from api.routes.delete import router as delete_router
from api.routes.get import router as get_router
from api.routes.list import router as list_router

router = APIRouter(tags=["jobs"])
router.include_router(create_router)
router.include_router(list_router)
router.include_router(get_router)
router.include_router(delete_router)
