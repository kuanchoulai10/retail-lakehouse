"""Define the discovery policy attachment API DTOs; the target DTOs are shared (``web.shared``)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from context.table_maintenance.adapter.inbound.web.shared import (
    PolicyTargetApiRequest,
    PolicyTargetApiResponse,
)


class AttachTableDiscoveryPolicyApiRequest(BaseModel):
    """Carry the target to attach the discovery policy to; it replaces whatever is attached there."""

    model_config = ConfigDict(extra="forbid")

    target: PolicyTargetApiRequest


class TableDiscoveryPolicyAttachmentApiResponse(BaseModel):
    """Describe a discovery policy attached to a target, under the attachment's ``da-`` id."""

    id: str
    target: PolicyTargetApiResponse
    policy_id: str
    policy_name: str
    attached_at: datetime


class ListedTableDiscoveryPolicyAttachmentApiResponse(BaseModel):
    """Describe a listed attachment; ``orphaned`` when its target no longer exists in the catalog."""

    id: str
    target: PolicyTargetApiResponse
    policy_id: str
    policy_name: str
    attached_at: datetime
    orphaned: bool


class TableDiscoveryPolicyAttachmentsApiResponse(BaseModel):
    """List a discovery policy's attachments."""

    attachments: list[ListedTableDiscoveryPolicyAttachmentApiResponse]
