"""Catalog REST API endpoints."""

from fastapi import APIRouter

from adapter.inbound.web.catalog.get_table import router as get_table_router
from adapter.inbound.web.catalog.list_branches import router as list_branches_router
from adapter.inbound.web.catalog.list_namespaces import (
    router as list_namespaces_router,
)
from adapter.inbound.web.catalog.list_snapshots import (
    router as list_snapshots_router,
)
from adapter.inbound.web.catalog.list_tables import router as list_tables_router
from adapter.inbound.web.catalog.list_tags import router as list_tags_router

router = APIRouter(tags=["catalog"])
router.include_router(list_namespaces_router)
router.include_router(list_tables_router)
router.include_router(get_table_router)
router.include_router(list_snapshots_router)
router.include_router(list_branches_router)
router.include_router(list_tags_router)
