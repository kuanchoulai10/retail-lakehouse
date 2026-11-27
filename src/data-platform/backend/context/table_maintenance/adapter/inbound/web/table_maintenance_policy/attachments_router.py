"""Define the maintenance policy attachment router."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from context.table_maintenance.adapter.inbound.web.shared import (
    PolicyTargetApiResponse,
    WebUseCases,
    use_cases_dependency,
)
from context.table_maintenance.adapter.inbound.web.table_maintenance_policy.attachments_dto import (
    AttachTableMaintenancePolicyApiRequest,
    ListedTableMaintenancePolicyAttachmentApiResponse,
    TableMaintenancePolicyAttachmentApiResponse,
    TableMaintenancePolicyAttachmentsApiResponse,
)
from context.table_maintenance.application.port.inbound.table_maintenance_policy import (
    AttachTableMaintenancePolicyUseCaseInput,
    DetachTableMaintenancePolicyUseCaseInput,
    ListTableMaintenancePolicyAttachmentsUseCaseInput,
)

attachments_router = APIRouter(prefix="/maintenance-policies", tags=["maintenance-policies"])

UseCases = Annotated[WebUseCases, Depends(use_cases_dependency)]


@attachments_router.get("/{name}/attachments")
def list_table_maintenance_policy_attachments(
    name: str, use_cases: UseCases
) -> TableMaintenancePolicyAttachmentsApiResponse:
    """List the catalogs, namespaces and tables a maintenance policy is attached to, marking those gone as orphaned."""
    output = use_cases.list_table_maintenance_policy_attachments.execute(
        ListTableMaintenancePolicyAttachmentsUseCaseInput(policy_name=name)
    )
    return TableMaintenancePolicyAttachmentsApiResponse(
        attachments=[
            ListedTableMaintenancePolicyAttachmentApiResponse(
                target=PolicyTargetApiResponse(type=item.type, path=list(item.path), table_uuid=item.table_uuid),
                policy_id=item.policy_id,
                policy_name=item.policy_name,
                orphaned=item.orphaned,
            )
            for item in output.items
        ]
    )


@attachments_router.put("/{name}/attachments")
def attach_table_maintenance_policy(
    name: str, body: AttachTableMaintenancePolicyApiRequest, use_cases: UseCases
) -> TableMaintenancePolicyAttachmentApiResponse:
    """Attach a maintenance policy to a catalog, namespace or table that exists, replacing the one it holds.

    A catalog the platform's credential cannot read answers 403, a namespace level holding a dot 422, and
    a place changed by someone else meanwhile 409.
    """
    output = use_cases.attach_table_maintenance_policy.execute(
        AttachTableMaintenancePolicyUseCaseInput(
            policy_name=name, target_type=body.target.type, path=tuple(body.target.path)
        )
    )
    return TableMaintenancePolicyAttachmentApiResponse(
        target=PolicyTargetApiResponse(type=output.target_type, path=list(output.path), table_uuid=output.table_uuid),
        policy_id=output.policy_id,
        policy_name=output.policy_name,
    )


@attachments_router.delete("/{name}/attachments", status_code=status.HTTP_204_NO_CONTENT)
def detach_table_maintenance_policy(
    name: str,
    target_type: Annotated[str, Query()],
    path: Annotated[list[str], Query()],
    use_cases: UseCases,
) -> Response:
    """Detach a maintenance policy from the place ``target_type`` and ``path`` name, whether or not it still exists.

    ``path`` repeats once per part: the catalog, the namespace levels, then the table name for a table.
    404 when the place does not hold this policy.
    """
    use_cases.detach_table_maintenance_policy.execute(
        DetachTableMaintenancePolicyUseCaseInput(policy_name=name, target_type=target_type, path=tuple(path))
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
