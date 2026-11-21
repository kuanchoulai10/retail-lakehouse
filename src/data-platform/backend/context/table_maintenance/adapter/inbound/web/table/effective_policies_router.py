"""Define the effective-policies router."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, Depends

from context.table_maintenance.adapter.inbound.web.shared import (
    PolicyTargetApiResponse,
    WebUseCases,
    use_cases_dependency,
)
from context.table_maintenance.adapter.inbound.web.table.effective_policies_dto import (
    DiscoveryEffectivePolicyApiResponse,
    EffectivePoliciesApiResponse,
    MaintenanceEffectivePolicyApiResponse,
)
from context.table_maintenance.application.port.inbound.table import GetEffectivePoliciesUseCaseInput

if TYPE_CHECKING:
    from context.table_maintenance.application.port.inbound.table import GetEffectivePoliciesUseCaseOutput

effective_policies_router = APIRouter(tags=["tables"])

UseCases = Annotated[WebUseCases, Depends(use_cases_dependency)]


@effective_policies_router.get("/tables/{table_uuid}/effective-policies")
def get_table_effective_policies(table_uuid: str, use_cases: UseCases) -> EffectivePoliciesApiResponse:
    """Return the policy of each kind that applies to a table table maintenance records, and the level it applies from.

    404 when table maintenance has no record of the uuid.
    """
    output = use_cases.get_effective_policies.execute(GetEffectivePoliciesUseCaseInput(table_uuid=table_uuid))
    return _response(output)


@effective_policies_router.get("/effective-policies")
def get_effective_policies(
    catalog: str, use_cases: UseCases, namespace: str | None = None, table: str | None = None
) -> EffectivePoliciesApiResponse:
    """Return the policy of each kind that applies to a catalog, a dot-joined namespace in it, or a table in it.

    A table is found in the catalog by name, so it need not be one table maintenance has a record of. 404
    when the catalog does not hold the catalog, namespace or table; 403 when the platform cannot read the catalog.
    """
    output = use_cases.get_effective_policies.execute(
        GetEffectivePoliciesUseCaseInput(catalog=catalog, namespace=namespace, table=table)
    )
    return _response(output)


def _response(output: GetEffectivePoliciesUseCaseOutput) -> EffectivePoliciesApiResponse:
    maintenance, discovery = output.maintenance, output.discovery
    return EffectivePoliciesApiResponse(
        policies=[
            MaintenanceEffectivePolicyApiResponse.model_validate(
                {**maintenance.model_dump(), "kind": "maintenance", "target": _target(maintenance.target)}
            ),
            DiscoveryEffectivePolicyApiResponse.model_validate(
                {**discovery.model_dump(), "kind": "discovery", "target": _target(discovery.target)}
            ),
        ]
    )


def _target(target: dict[str, Any] | None) -> PolicyTargetApiResponse | None:
    if target is None:
        return None
    return PolicyTargetApiResponse(type=target["type"], path=target["path"], table_uuid=target.get("table_uuid"))
