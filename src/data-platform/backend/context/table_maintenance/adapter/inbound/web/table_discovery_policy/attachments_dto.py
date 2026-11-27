"""Define the discovery policy attachment API DTOs; the target DTOs are shared (``web.shared``)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from context.table_maintenance.adapter.inbound.web.shared import (
    PolicyTargetApiRequest,
    PolicyTargetApiResponse,
)


class AttachTableDiscoveryPolicyApiRequest(BaseModel):
    """Carry the catalog, namespace or table to attach the discovery policy to; it replaces the one held there."""

    model_config = ConfigDict(extra="forbid")

    target: PolicyTargetApiRequest


class TableDiscoveryPolicyAttachmentApiResponse(BaseModel):
    """Describe a discovery policy attached to a catalog, namespace or table."""

    target: PolicyTargetApiResponse
    policy_id: str
    policy_name: str


class ListedTableDiscoveryPolicyAttachmentApiResponse(BaseModel):
    """Describe a place the policy is attached to; ``orphaned`` when it no longer exists in the catalog."""

    target: PolicyTargetApiResponse
    policy_id: str
    policy_name: str
    orphaned: bool


class TableDiscoveryPolicyAttachmentsApiResponse(BaseModel):
    """List the places a discovery policy is attached to: catalogs, then namespaces, then tables, each by path."""

    attachments: list[ListedTableDiscoveryPolicyAttachmentApiResponse]
