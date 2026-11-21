"""Define the discovery policy attachment router."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from context.table_maintenance.adapter.inbound.web.shared import (
    PolicyTargetApiResponse,
    WebUseCases,
    use_cases_dependency,
)
from context.table_maintenance.adapter.inbound.web.table_discovery_policy_attachment.dto import (
    AttachTableDiscoveryPolicyApiRequest,
    ListedTableDiscoveryPolicyAttachmentApiResponse,
    TableDiscoveryPolicyAttachmentApiResponse,
    TableDiscoveryPolicyAttachmentsApiResponse,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy_attachment import (
    AttachTableDiscoveryPolicyUseCaseInput,
    DetachTableDiscoveryPolicyUseCaseInput,
    ListTableDiscoveryPolicyAttachmentsUseCaseInput,
)

router = APIRouter(prefix="/discovery-policies", tags=["discovery-policies"])

UseCases = Annotated[WebUseCases, Depends(use_cases_dependency)]


@router.get("/{name}/attachments")
def list_table_discovery_policy_attachments(
    name: str, use_cases: UseCases
) -> TableDiscoveryPolicyAttachmentsApiResponse:
    """List the targets a discovery policy is attached to, marking those no longer in the catalog as orphaned."""
    output = use_cases.list_table_discovery_policy_attachments.execute(
        ListTableDiscoveryPolicyAttachmentsUseCaseInput(policy_name=name)
    )
    return TableDiscoveryPolicyAttachmentsApiResponse(
        attachments=[
            ListedTableDiscoveryPolicyAttachmentApiResponse(
                id=item.id,
                target=PolicyTargetApiResponse(type=item.type, path=list(item.path), table_uuid=item.table_uuid),
                policy_id=item.policy_id,
                policy_name=item.policy_name,
                attached_at=item.attached_at,
                orphaned=item.orphaned,
            )
            for item in output.items
        ]
    )


@router.put("/{name}/attachments")
def attach_table_discovery_policy(
    name: str, body: AttachTableDiscoveryPolicyApiRequest, use_cases: UseCases
) -> TableDiscoveryPolicyAttachmentApiResponse:
    """Attach a discovery policy to a target that exists in the catalog, replacing the target's attachment.

    The target keeps its attachment's id. A catalog the platform's credential cannot read answers 403.
    """
    output = use_cases.attach_table_discovery_policy.execute(
        AttachTableDiscoveryPolicyUseCaseInput(
            policy_name=name, target_type=body.target.type, path=tuple(body.target.path)
        )
    )
    return TableDiscoveryPolicyAttachmentApiResponse(
        id=output.id,
        target=PolicyTargetApiResponse(type=output.target_type, path=list(output.path), table_uuid=output.table_uuid),
        policy_id=output.policy_id,
        policy_name=output.policy_name,
        attached_at=output.attached_at,
    )


@router.delete("/{name}/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
def detach_table_discovery_policy(name: str, attachment_id: str, use_cases: UseCases) -> Response:
    """Detach one of a discovery policy's attachments by its ``da-`` id, whether or not its target still exists.

    404 when the policy has no such attachment.
    """
    use_cases.detach_table_discovery_policy.execute(
        DetachTableDiscoveryPolicyUseCaseInput(policy_name=name, attachment_id=attachment_id)
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
