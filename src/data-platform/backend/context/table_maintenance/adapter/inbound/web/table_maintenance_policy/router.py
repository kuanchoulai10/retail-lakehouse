"""Define the maintenance policy router."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, Response, status

from context.table_maintenance.adapter.inbound.web.shared import (
    WebUseCases,
    use_cases_dependency,
)
from context.table_maintenance.adapter.inbound.web.table_maintenance_policy.dto import (
    CreateTableMaintenancePolicyApiRequest,
    ListedTableMaintenancePolicyApiResponse,
    TableMaintenancePoliciesApiResponse,
    TableMaintenancePolicyApiResponse,
    TableMaintenancePolicyVersionApiResponse,
    UpdateTableMaintenancePolicyApiRequest,
)
from context.table_maintenance.application.port.inbound.table_maintenance_policy import (
    CreateTableMaintenancePolicyUseCaseInput,
    DeleteTableMaintenancePolicyUseCaseInput,
    GetTableMaintenancePolicyUseCaseInput,
    GetTableMaintenancePolicyVersionUseCaseInput,
    ListTableMaintenancePoliciesUseCaseInput,
    UpdateTableMaintenancePolicyUseCaseInput,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.inbound.table_maintenance_policy import (
        CreateTableMaintenancePolicyUseCaseOutput,
        GetTableMaintenancePolicyUseCaseOutput,
        UpdateTableMaintenancePolicyUseCaseOutput,
    )

router = APIRouter(prefix="/maintenance-policies", tags=["maintenance-policies"])

UseCases = Annotated[WebUseCases, Depends(use_cases_dependency)]


def _policy_response(
    output: CreateTableMaintenancePolicyUseCaseOutput
    | GetTableMaintenancePolicyUseCaseOutput
    | UpdateTableMaintenancePolicyUseCaseOutput,
) -> TableMaintenancePolicyApiResponse:
    return TableMaintenancePolicyApiResponse.model_validate(
        {
            "name": output.name,
            "version": output.version,
            "created_at": output.created_at,
            "updated_at": output.updated_at,
            **output.content,
        }
    )


@router.get("")
def list_table_maintenance_policies(use_cases: UseCases) -> TableMaintenancePoliciesApiResponse:
    """List every policy at its current version with its attachment count."""
    output = use_cases.list_table_maintenance_policies.execute(ListTableMaintenancePoliciesUseCaseInput())
    return TableMaintenancePoliciesApiResponse(
        policies=[
            ListedTableMaintenancePolicyApiResponse.model_validate(
                {
                    "name": item.name,
                    "version": item.version,
                    "created_at": item.created_at,
                    "updated_at": item.updated_at,
                    "attachment_count": item.attachment_count,
                    **item.content,
                }
            )
            for item in output.items
        ]
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_table_maintenance_policy(
    body: CreateTableMaintenancePolicyApiRequest, use_cases: UseCases
) -> TableMaintenancePolicyApiResponse:
    """Create a policy at version 1."""
    output = use_cases.create_table_maintenance_policy.execute(
        CreateTableMaintenancePolicyUseCaseInput(name=body.name, content=body.model_dump(exclude={"name"}))
    )
    return _policy_response(output)


@router.get("/{name}")
def get_table_maintenance_policy(name: str, use_cases: UseCases) -> TableMaintenancePolicyApiResponse:
    """Return a policy at its current version."""
    output = use_cases.get_table_maintenance_policy.execute(GetTableMaintenancePolicyUseCaseInput(name=name))
    return _policy_response(output)


@router.put("/{name}")
def update_table_maintenance_policy(
    name: str, body: UpdateTableMaintenancePolicyApiRequest, use_cases: UseCases
) -> TableMaintenancePolicyApiResponse:
    """Replace a policy's content from the version read (409 if stale); the version increments."""
    output = use_cases.update_table_maintenance_policy.execute(
        UpdateTableMaintenancePolicyUseCaseInput(
            name=name, content=body.model_dump(exclude={"version"}), version=body.version
        )
    )
    return _policy_response(output)


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_table_maintenance_policy(name: str, use_cases: UseCases) -> Response:
    """Delete a policy and its versions; 409 while it is attached or when it is the default."""
    use_cases.delete_table_maintenance_policy.execute(DeleteTableMaintenancePolicyUseCaseInput(name=name))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{name}/versions/{version}")
def get_table_maintenance_policy_version(
    name: str, version: int, use_cases: UseCases
) -> TableMaintenancePolicyVersionApiResponse:
    """Return one stored version of a policy."""
    output = use_cases.get_table_maintenance_policy_version.execute(
        GetTableMaintenancePolicyVersionUseCaseInput(name=name, version=version)
    )
    return TableMaintenancePolicyVersionApiResponse.model_validate(
        {"name": output.name, "version": output.version, "created_at": output.created_at, **output.content}
    )
