"""Define the maintenance policy attachment DTOs; the target DTOs are shared (``web.shared``)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from context.table_maintenance.adapter.inbound.web.shared import (
    PolicyTargetApiRequest,
    PolicyTargetApiResponse,
)


class AttachTableMaintenancePolicyApiRequest(BaseModel):
    """Carry the target to attach the policy to; it replaces whatever is attached there."""

    model_config = ConfigDict(extra="forbid")

    target: PolicyTargetApiRequest


class TableMaintenancePolicyAttachmentApiResponse(BaseModel):
    """Describe a maintenance policy attached to a target, under the attachment's ``pa-`` id."""

    id: str
    target: PolicyTargetApiResponse
    policy_id: str
    policy_name: str
    attached_at: datetime


class ListedTableMaintenancePolicyAttachmentApiResponse(BaseModel):
    """Describe a listed attachment; ``orphaned`` when its target no longer exists in the catalog."""

    id: str
    target: PolicyTargetApiResponse
    policy_id: str
    policy_name: str
    attached_at: datetime
    orphaned: bool


class TableMaintenancePolicyAttachmentsApiResponse(BaseModel):
    """List a maintenance policy's attachments."""

    attachments: list[ListedTableMaintenancePolicyAttachmentApiResponse]
