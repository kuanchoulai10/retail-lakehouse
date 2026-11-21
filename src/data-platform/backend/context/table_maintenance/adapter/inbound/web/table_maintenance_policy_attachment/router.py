"""Define the policy mapping and applicable policy router."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, Response, status

from context.table_maintenance.adapter.inbound.web.shared import (
    PolicyTargetApiResponse,
    WebUseCases,
    use_cases_dependency,
)
from context.table_maintenance.adapter.inbound.web.table_maintenance_policy_attachment.dto import (
    ApplicableTableMaintenancePolicyApiResponse,
    AttachTableMaintenancePolicyApiRequest,
    DetachTableMaintenancePolicyApiRequest,
    ListedTableMaintenancePolicyMappingApiResponse,
    TableMaintenancePolicyMappingApiResponse,
    TableMaintenancePolicyMappingsApiResponse,
)
from context.table_maintenance.application.port.inbound.table_maintenance_policy_attachment import (
    AttachTableMaintenancePolicyUseCaseInput,
    DetachTableMaintenancePolicyUseCaseInput,
    ListTableMaintenancePolicyAttachmentsUseCaseInput,
    ResolveApplicableTableMaintenancePolicyUseCaseInput,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.inbound.table_maintenance_policy_attachment import (
        ResolveApplicableTableMaintenancePolicyUseCaseOutput,
    )

router = APIRouter(tags=["maintenance-policies"])

UseCases = Annotated[WebUseCases, Depends(use_cases_dependency)]


@router.get("/maintenance-policies/{name}/mappings")
def list_table_maintenance_policy_mappings(name: str, use_cases: UseCases) -> TableMaintenancePolicyMappingsApiResponse:
    """List the targets a policy is attached to, marking those no longer in the catalog as orphaned."""
    output = use_cases.list_table_maintenance_policy_attachments.execute(
        ListTableMaintenancePolicyAttachmentsUseCaseInput(policy_name=name)
    )
    return TableMaintenancePolicyMappingsApiResponse(
        mappings=[
            ListedTableMaintenancePolicyMappingApiResponse(
                target=PolicyTargetApiResponse(type=item.type, path=list(item.path), table_uuid=item.table_uuid),
                policy_id=item.policy_id,
                policy_name=item.policy_name,
                attached_at=item.attached_at,
                orphaned=item.orphaned,
            )
            for item in output.items
        ]
    )


@router.put("/maintenance-policies/{name}/mappings")
def attach_table_maintenance_policy(
    name: str, body: AttachTableMaintenancePolicyApiRequest, use_cases: UseCases
) -> TableMaintenancePolicyMappingApiResponse:
    """Attach a policy to a target that exists in the catalog, replacing the target's attachment."""
    output = use_cases.attach_table_maintenance_policy.execute(
        AttachTableMaintenancePolicyUseCaseInput(
            target_type=body.target.type, path=tuple(body.target.path), policy_name=name
        )
    )
    return TableMaintenancePolicyMappingApiResponse(
        target=PolicyTargetApiResponse(type=output.target_type, path=list(output.path), table_uuid=output.table_uuid),
        policy_id=output.policy_id,
        policy_name=output.policy_name,
        attached_at=output.attached_at,
    )


@router.delete("/maintenance-policies/{name}/mappings", status_code=status.HTTP_204_NO_CONTENT)
def detach_table_maintenance_policy(
    name: str, body: DetachTableMaintenancePolicyApiRequest, use_cases: UseCases
) -> Response:
    """Detach a policy from a target; 404 when that policy is not the one attached there."""
    use_cases.detach_table_maintenance_policy.execute(
        DetachTableMaintenancePolicyUseCaseInput(
            target_type=body.target.type,
            path=tuple(body.target.path),
            table_uuid=body.target.table_uuid,
            policy_name=name,
        )
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/tables/{table_uuid}/applicable-policy")
def get_table_applicable_maintenance_policy(
    table_uuid: str, use_cases: UseCases
) -> ApplicableTableMaintenancePolicyApiResponse:
    """Return the policy that applies to a table, its version and the target it is inherited from."""
    output = use_cases.resolve_applicable_table_maintenance_policy.execute(
        ResolveApplicableTableMaintenancePolicyUseCaseInput(table_uuid=table_uuid)
    )
    return _applicable_response(output)


@router.get("/applicable-policy")
def get_applicable_maintenance_policy(
    catalog: str, use_cases: UseCases, namespace: str | None = None, table: str | None = None
) -> ApplicableTableMaintenancePolicyApiResponse:
    """Return the policy that applies to a catalog, a dot-joined namespace in it, or a table in that namespace.

    A table is found in the catalog by name, so it need not be one table maintenance has a record of;
    404 when the catalog does not hold it.
    """
    output = use_cases.resolve_applicable_table_maintenance_policy.execute(
        ResolveApplicableTableMaintenancePolicyUseCaseInput(catalog=catalog, namespace=namespace, table=table)
    )
    return _applicable_response(output)


def _applicable_response(
    output: ResolveApplicableTableMaintenancePolicyUseCaseOutput,
) -> ApplicableTableMaintenancePolicyApiResponse:
    target = output.target
    return ApplicableTableMaintenancePolicyApiResponse.model_validate(
        {
            "id": output.policy_id,
            "name": output.policy_name,
            "version": output.version,
            "target": None
            if target is None
            else {"type": target["type"], "path": target["path"], "table_uuid": target.get("table_uuid")},
            **output.content,
        }
    )
