"""Define the discovery rule router."""

from __future__ import annotations

from typing import Annotated

from adapter.inbound.web.table_discovery_rule.dto import (
    CreateTableDiscoveryRuleApiRequest,
    TableDiscoveryRuleApiResponse,
    UpdateTableDiscoveryRuleApiRequest,
)
from adapter.inbound.web import web_use_cases, WebUseCases
from application.port.inbound.table_discovery_rule import (
    CreateTableDiscoveryRuleUseCaseInput,
    DeleteTableDiscoveryRuleUseCaseInput,
    ListTableDiscoveryRulesUseCaseInput,
    UpdateTableDiscoveryRuleUseCaseInput,
)
from fastapi import APIRouter, Depends, Response, status

router = APIRouter(prefix="/table-discovery-rules", tags=["table-discovery-rules"])

UseCases = Annotated[WebUseCases, Depends(web_use_cases)]


@router.get("")
def list_table_discovery_rules(
    use_cases: UseCases,
) -> list[TableDiscoveryRuleApiResponse]:
    """List the discovery rules."""
    output = use_cases.list_table_discovery_rules.execute(
        ListTableDiscoveryRulesUseCaseInput()
    )
    return [TableDiscoveryRuleApiResponse.model_validate(item) for item in output.items]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_table_discovery_rule(
    body: CreateTableDiscoveryRuleApiRequest, use_cases: UseCases
) -> TableDiscoveryRuleApiResponse:
    """Create a discovery rule."""
    output = use_cases.create_table_discovery_rule.execute(
        CreateTableDiscoveryRuleUseCaseInput(**body.model_dump())
    )
    return TableDiscoveryRuleApiResponse.model_validate(output)


@router.patch("/{rule_id}")
def update_table_discovery_rule(
    rule_id: str, body: UpdateTableDiscoveryRuleApiRequest, use_cases: UseCases
) -> TableDiscoveryRuleApiResponse:
    """Replace the fields of a discovery rule."""
    output = use_cases.update_table_discovery_rule.execute(
        UpdateTableDiscoveryRuleUseCaseInput(id=rule_id, **body.model_dump())
    )
    return TableDiscoveryRuleApiResponse.model_validate(output)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_table_discovery_rule(rule_id: str, use_cases: UseCases) -> Response:
    """Delete a discovery rule."""
    use_cases.delete_table_discovery_rule.execute(
        DeleteTableDiscoveryRuleUseCaseInput(id=rule_id)
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
