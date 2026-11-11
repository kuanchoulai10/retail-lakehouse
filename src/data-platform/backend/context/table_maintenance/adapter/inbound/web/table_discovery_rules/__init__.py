"""Web adapter for the table_discovery_rules group."""

from __future__ import annotations

from context.table_maintenance.adapter.inbound.web.table_discovery_rules.dto import (
    CoveredCatalogsApiResponse,
    DiscoveryPreviewTableApiResponse,
    PreviewTableDiscoveryRulesApiRequest,
    PreviewTableDiscoveryRulesApiResponse,
    ReplaceTableDiscoveryRulesApiRequest,
    TableDiscoveryRuleApiRequest,
    TableDiscoveryRuleApiResponse,
    TableDiscoveryRulesApiResponse,
)
from context.table_maintenance.adapter.inbound.web.table_discovery_rules.router import (
    router,
)

__all__ = [
    "CoveredCatalogsApiResponse",
    "DiscoveryPreviewTableApiResponse",
    "PreviewTableDiscoveryRulesApiRequest",
    "PreviewTableDiscoveryRulesApiResponse",
    "ReplaceTableDiscoveryRulesApiRequest",
    "TableDiscoveryRuleApiRequest",
    "TableDiscoveryRuleApiResponse",
    "TableDiscoveryRulesApiResponse",
    "router",
]
