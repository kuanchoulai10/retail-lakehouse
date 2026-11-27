"""Define the discovery policy attachment router."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from context.table_maintenance.adapter.inbound.web.shared import (
    PolicyTargetApiResponse,
    WebUseCases,
    use_cases_dependency,
)
from context.table_maintenance.adapter.inbound.web.table_discovery_policy.attachments_dto import (
    AttachTableDiscoveryPolicyApiRequest,
    ListedTableDiscoveryPolicyAttachmentApiResponse,
    TableDiscoveryPolicyAttachmentApiResponse,
    TableDiscoveryPolicyAttachmentsApiResponse,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy import (
    AttachTableDiscoveryPolicyUseCaseInput,
    DetachTableDiscoveryPolicyUseCaseInput,
    ListTableDiscoveryPolicyAttachmentsUseCaseInput,
)

attachments_router = APIRouter(prefix="/discovery-policies", tags=["discovery-policies"])

UseCases = Annotated[WebUseCases, Depends(use_cases_dependency)]


@attachments_router.get("/{name}/attachments")
def list_table_discovery_policy_attachments(
    name: str, use_cases: UseCases
) -> TableDiscoveryPolicyAttachmentsApiResponse:
    """List the catalogs, namespaces and tables a discovery policy is attached to, marking those gone as orphaned."""
    output = use_cases.list_table_discovery_policy_attachments.execute(
        ListTableDiscoveryPolicyAttachmentsUseCaseInput(policy_name=name)
    )
    return TableDiscoveryPolicyAttachmentsApiResponse(
        attachments=[
            ListedTableDiscoveryPolicyAttachmentApiResponse(
                target=PolicyTargetApiResponse(type=item.type, path=list(item.path), table_uuid=item.table_uuid),
                policy_id=item.policy_id,
                policy_name=item.policy_name,
                orphaned=item.orphaned,
            )
            for item in output.items
        ]
    )


@attachments_router.put("/{name}/attachments")
def attach_table_discovery_policy(
    name: str, body: AttachTableDiscoveryPolicyApiRequest, use_cases: UseCases
) -> TableDiscoveryPolicyAttachmentApiResponse:
    """Attach a discovery policy to a catalog, namespace or table that exists, replacing the one it holds.

    A catalog the platform's credential cannot read answers 403, and a namespace level holding a dot 422.
    """
    output = use_cases.attach_table_discovery_policy.execute(
        AttachTableDiscoveryPolicyUseCaseInput(
            policy_name=name, target_type=body.target.type, path=tuple(body.target.path)
        )
    )
    return TableDiscoveryPolicyAttachmentApiResponse(
        target=PolicyTargetApiResponse(type=output.target_type, path=list(output.path), table_uuid=output.table_uuid),
        policy_id=output.policy_id,
        policy_name=output.policy_name,
    )


@attachments_router.delete("/{name}/attachments", status_code=status.HTTP_204_NO_CONTENT)
def detach_table_discovery_policy(
    name: str,
    target_type: Annotated[str, Query()],
    path: Annotated[list[str], Query()],
    use_cases: UseCases,
) -> Response:
    """Detach a discovery policy from the place ``target_type`` and ``path`` name, whether or not it still exists.

    ``path`` repeats once per part: the catalog, the namespace levels, then the table name for a table.
    404 when the place does not hold this policy.
    """
    use_cases.detach_table_discovery_policy.execute(
        DetachTableDiscoveryPolicyUseCaseInput(policy_name=name, target_type=target_type, path=tuple(path))
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
