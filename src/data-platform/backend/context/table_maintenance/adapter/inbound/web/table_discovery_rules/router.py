"""Define the discovery rules router."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from context.table_maintenance.adapter.inbound.web.shared import (
    WebUseCases,
    use_cases_dependency,
)
from context.table_maintenance.adapter.inbound.web.table_discovery_rules.dto import (
    CoveredCatalogsApiResponse,
    ReplaceTableDiscoveryRulesApiRequest,
    TableDiscoveryRulesApiResponse,
)
from context.table_maintenance.application.port.inbound.table_discovery_rules import (
    GetTableDiscoveryRulesUseCaseInput,
    ListCoveredCatalogsUseCaseInput,
    ReplaceTableDiscoveryRulesUseCaseInput,
)

router = APIRouter(prefix="/discovery-rules", tags=["discovery-rules"])

UseCases = Annotated[WebUseCases, Depends(use_cases_dependency)]


@router.get("")
def get_table_discovery_rules(use_cases: UseCases) -> TableDiscoveryRulesApiResponse:
    """Return the discovery rules in priority order with the list's version."""
    output = use_cases.get_table_discovery_rules.execute(GetTableDiscoveryRulesUseCaseInput())
    return TableDiscoveryRulesApiResponse.model_validate(output)


@router.put("")
def replace_table_discovery_rules(
    body: ReplaceTableDiscoveryRulesApiRequest, use_cases: UseCases
) -> TableDiscoveryRulesApiResponse:
    """Replace the whole rule list from the version read, then discover tables in every covered catalog."""
    output = use_cases.replace_table_discovery_rules.execute(
        ReplaceTableDiscoveryRulesUseCaseInput(
            version=body.version,
            rules=tuple(
                ReplaceTableDiscoveryRulesUseCaseInput.TableDiscoveryRule(
                    id=rule.id,
                    priority=rule.priority,
                    action=rule.action,
                    enabled=rule.enabled,
                    catalogs=tuple(rule.catalogs),
                    namespaces=tuple(rule.namespaces),
                    tables=tuple(rule.tables),
                )
                for rule in body.rules
            ),
        )
    )
    return TableDiscoveryRulesApiResponse.model_validate(output)


@router.get("/catalogs")
def list_covered_catalogs(use_cases: UseCases) -> CoveredCatalogsApiResponse:
    """List the catalogs maintenance covers."""
    output = use_cases.list_covered_catalogs.execute(ListCoveredCatalogsUseCaseInput())
    return CoveredCatalogsApiResponse.model_validate(output)
