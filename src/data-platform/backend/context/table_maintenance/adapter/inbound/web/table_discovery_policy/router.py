"""Define the discovery policy router."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, Response, status

from context.table_maintenance.adapter.inbound.web.shared import (
    WebUseCases,
    use_cases_dependency,
)
from context.table_maintenance.adapter.inbound.web.table_discovery_policy.dto import (
    CreateTableDiscoveryPolicyApiRequest,
    ListedTableDiscoveryPolicyApiResponse,
    TableDiscoveryPoliciesApiResponse,
    TableDiscoveryPolicyApiResponse,
    TableDiscoveryPolicyVersionApiResponse,
    UpdateTableDiscoveryPolicyApiRequest,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy import (
    CreateTableDiscoveryPolicyUseCaseInput,
    DeleteTableDiscoveryPolicyUseCaseInput,
    GetTableDiscoveryPolicyUseCaseInput,
    GetTableDiscoveryPolicyVersionUseCaseInput,
    ListTableDiscoveryPoliciesUseCaseInput,
    UpdateTableDiscoveryPolicyUseCaseInput,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.inbound.table_discovery_policy import (
        CreateTableDiscoveryPolicyUseCaseOutput,
        GetTableDiscoveryPolicyUseCaseOutput,
        UpdateTableDiscoveryPolicyUseCaseOutput,
    )

router = APIRouter(prefix="/discovery-policies", tags=["discovery-policies"])

UseCases = Annotated[WebUseCases, Depends(use_cases_dependency)]


def _policy_response(
    output: CreateTableDiscoveryPolicyUseCaseOutput
    | GetTableDiscoveryPolicyUseCaseOutput
    | UpdateTableDiscoveryPolicyUseCaseOutput,
) -> TableDiscoveryPolicyApiResponse:
    return TableDiscoveryPolicyApiResponse.model_validate(
        {
            "id": output.id,
            "name": output.name,
            "version": output.version,
            "created_at": output.created_at,
            "updated_at": output.updated_at,
            "description": output.description,
            "rules": list(output.rules),
        }
    )


@router.get("")
def list_table_discovery_policies(use_cases: UseCases) -> TableDiscoveryPoliciesApiResponse:
    """List every discovery policy at its current version with its attachment count, by name."""
    output = use_cases.list_table_discovery_policies.execute(ListTableDiscoveryPoliciesUseCaseInput())
    return TableDiscoveryPoliciesApiResponse(
        policies=[
            ListedTableDiscoveryPolicyApiResponse.model_validate(
                {
                    "id": item.id,
                    "name": item.name,
                    "version": item.version,
                    "created_at": item.created_at,
                    "updated_at": item.updated_at,
                    "description": item.description,
                    "rules": list(item.rules),
                    "attachment_count": item.attachment_count,
                }
            )
            for item in output.items
        ]
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_table_discovery_policy(
    body: CreateTableDiscoveryPolicyApiRequest, use_cases: UseCases
) -> TableDiscoveryPolicyApiResponse:
    """Create a discovery policy at version 1 with the rules in the order sent."""
    output = use_cases.create_table_discovery_policy.execute(
        CreateTableDiscoveryPolicyUseCaseInput(
            name=body.name, description=body.description, rules=tuple(r.model_dump() for r in body.rules)
        )
    )
    return _policy_response(output)


@router.get("/{name}")
def get_table_discovery_policy(name: str, use_cases: UseCases) -> TableDiscoveryPolicyApiResponse:
    """Return a discovery policy at its current version."""
    output = use_cases.get_table_discovery_policy.execute(GetTableDiscoveryPolicyUseCaseInput(name=name))
    return _policy_response(output)


@router.put("/{name}")
def update_table_discovery_policy(
    name: str, body: UpdateTableDiscoveryPolicyApiRequest, use_cases: UseCases
) -> TableDiscoveryPolicyApiResponse:
    """Revise a discovery policy from the version read (409 if stale); the version increments."""
    output = use_cases.update_table_discovery_policy.execute(
        UpdateTableDiscoveryPolicyUseCaseInput(
            name=name,
            description=body.description,
            rules=tuple(r.model_dump() for r in body.rules),
            version=body.version,
        )
    )
    return _policy_response(output)


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_table_discovery_policy(name: str, use_cases: UseCases) -> Response:
    """Delete a discovery policy and its versions; 409 while it is attached."""
    use_cases.delete_table_discovery_policy.execute(DeleteTableDiscoveryPolicyUseCaseInput(name=name))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{name}/versions/{version}")
def get_table_discovery_policy_version(
    name: str, version: int, use_cases: UseCases
) -> TableDiscoveryPolicyVersionApiResponse:
    """Return one stored version of a discovery policy."""
    output = use_cases.get_table_discovery_policy_version.execute(
        GetTableDiscoveryPolicyVersionUseCaseInput(name=name, version=version)
    )
    return TableDiscoveryPolicyVersionApiResponse.model_validate(
        {
            "id": output.id,
            "name": output.name,
            "version": output.version,
            "created_at": output.created_at,
            "description": output.description,
            "rules": list(output.rules),
        }
    )
