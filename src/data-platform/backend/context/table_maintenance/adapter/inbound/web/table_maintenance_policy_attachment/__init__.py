"""Web adapter for the table_maintenance_policy_attachment group: policy mappings and applicable policies."""

from __future__ import annotations

from context.table_maintenance.adapter.inbound.web.table_maintenance_policy_attachment.dto import (
    ApplicableTableMaintenancePolicyApiResponse,
    AttachTableMaintenancePolicyApiRequest,
    DetachPolicyTargetApiRequest,
    DetachTableMaintenancePolicyApiRequest,
    ListedTableMaintenancePolicyMappingApiResponse,
    PolicyTargetApiRequest,
    PolicyTargetApiResponse,
    TableMaintenancePolicyMappingApiResponse,
    TableMaintenancePolicyMappingsApiResponse,
)
from context.table_maintenance.adapter.inbound.web.table_maintenance_policy_attachment.router import (
    router,
)

__all__ = [
    "ApplicableTableMaintenancePolicyApiResponse",
    "AttachTableMaintenancePolicyApiRequest",
    "DetachPolicyTargetApiRequest",
    "DetachTableMaintenancePolicyApiRequest",
    "ListedTableMaintenancePolicyMappingApiResponse",
    "PolicyTargetApiRequest",
    "PolicyTargetApiResponse",
    "TableMaintenancePolicyMappingApiResponse",
    "TableMaintenancePolicyMappingsApiResponse",
    "router",
]
