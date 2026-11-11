"""Define the policy mapping and applicable policy API DTOs.

A target is ``{"type", "path"}`` as in Polaris's policy mappings, with the catalog as the first path
element because this API is not scoped to one catalog: ``[catalog]``, ``[catalog, ns1, ...]`` or
``[catalog, ns1, ..., table]``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from context.table_maintenance.adapter.inbound.web.table_maintenance_policy import OperationPoliciesApiRequest

PolicyTargetKind = Literal["catalog", "namespace", "table"]


class PolicyTargetApiRequest(BaseModel):
    """Name a catalog, namespace or table to attach a policy to."""

    model_config = ConfigDict(extra="forbid")

    type: PolicyTargetKind
    path: list[str]


class DetachPolicyTargetApiRequest(BaseModel):
    """Name the target to detach from; a table no longer in the catalog is named by its ``table_uuid``."""

    model_config = ConfigDict(extra="forbid")

    type: PolicyTargetKind
    path: list[str]
    table_uuid: str | None = None


class AttachTableMaintenancePolicyApiRequest(BaseModel):
    """Carry the target to attach the policy to; it replaces whatever is attached there."""

    model_config = ConfigDict(extra="forbid")

    target: PolicyTargetApiRequest


class DetachTableMaintenancePolicyApiRequest(BaseModel):
    """Carry the target to detach the policy from."""

    model_config = ConfigDict(extra="forbid")

    target: DetachPolicyTargetApiRequest


class PolicyTargetApiResponse(BaseModel):
    """Describe a target; a table target carries the uuid it is keyed by."""

    type: str
    path: list[str]
    table_uuid: str | None


class TableMaintenancePolicyMappingApiResponse(BaseModel):
    """Describe a policy attached to a target."""

    target: PolicyTargetApiResponse
    policy_name: str
    attached_at: datetime


class ListedTableMaintenancePolicyMappingApiResponse(BaseModel):
    """Describe a listed mapping; ``orphaned`` when its target is no longer in the catalog."""

    target: PolicyTargetApiResponse
    policy_name: str
    attached_at: datetime
    orphaned: bool


class TableMaintenancePolicyMappingsApiResponse(BaseModel):
    """List a policy's mappings."""

    mappings: list[ListedTableMaintenancePolicyMappingApiResponse]


class ApplicableTableMaintenancePolicyApiResponse(BaseModel):
    """Describe the policy that applies after inheritance and the target it is attached to, null for the default."""

    name: str
    version: int
    description: str
    reconcile_interval_seconds: int
    dry_run: bool
    operations: OperationPoliciesApiRequest
    target: PolicyTargetApiResponse | None
