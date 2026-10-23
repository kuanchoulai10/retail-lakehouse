"""Define the discovery rule router."""

from __future__ import annotations

from typing import Annotated

from adapter.inbound.web.discovery_rule.dto import (
    CreateDiscoveryRuleApiRequest,
    DiscoveryRuleApiResponse,
    UpdateDiscoveryRuleApiRequest,
)
from adapter.inbound.web.use_cases_dependency import web_use_cases
from adapter.inbound.web.web_use_cases import WebUseCases
from application.port.inbound.discovery_rule.create_discovery_rule import (
    CreateDiscoveryRuleUseCaseInput,
)
from application.port.inbound.discovery_rule.delete_discovery_rule import (
    DeleteDiscoveryRuleUseCaseInput,
)
from application.port.inbound.discovery_rule.list_discovery_rules import (
    ListDiscoveryRulesUseCaseInput,
)
from application.port.inbound.discovery_rule.update_discovery_rule import (
    UpdateDiscoveryRuleUseCaseInput,
)
from fastapi import APIRouter, Depends, Response, status

router = APIRouter(prefix="/discovery-rules", tags=["discovery-rules"])

UseCases = Annotated[WebUseCases, Depends(web_use_cases)]


@router.get("")
def list_discovery_rules(use_cases: UseCases) -> list[DiscoveryRuleApiResponse]:
    """List the discovery rules."""
    output = use_cases.list_discovery_rules.execute(ListDiscoveryRulesUseCaseInput())
    return [DiscoveryRuleApiResponse.model_validate(item) for item in output.items]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_discovery_rule(
    body: CreateDiscoveryRuleApiRequest, use_cases: UseCases
) -> DiscoveryRuleApiResponse:
    """Create a discovery rule."""
    output = use_cases.create_discovery_rule.execute(
        CreateDiscoveryRuleUseCaseInput(**body.model_dump())
    )
    return DiscoveryRuleApiResponse.model_validate(output)


@router.patch("/{rule_id}")
def update_discovery_rule(
    rule_id: str, body: UpdateDiscoveryRuleApiRequest, use_cases: UseCases
) -> DiscoveryRuleApiResponse:
    """Replace the fields of a discovery rule."""
    output = use_cases.update_discovery_rule.execute(
        UpdateDiscoveryRuleUseCaseInput(id=rule_id, **body.model_dump())
    )
    return DiscoveryRuleApiResponse.model_validate(output)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_discovery_rule(rule_id: str, use_cases: UseCases) -> Response:
    """Delete a discovery rule."""
    use_cases.delete_discovery_rule.execute(DeleteDiscoveryRuleUseCaseInput(id=rule_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
