"""Outbound ports for the catalog group."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.catalog import Catalog
from context.table_maintenance.application.domain.model.shared import (
    CatalogId,
    TableDiscoveryPolicyId,
    TableMaintenancePolicyId,
)
from context.table_maintenance.application.port.outbound.catalog.catalogs_repo import CatalogsRepo

__all__ = [
    "Catalog",
    "CatalogId",
    "CatalogsRepo",
    "TableDiscoveryPolicyId",
    "TableMaintenancePolicyId",
]
