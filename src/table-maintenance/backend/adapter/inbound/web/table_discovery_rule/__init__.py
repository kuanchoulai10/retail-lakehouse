"""Web adapter for the table_discovery_rule group."""

from __future__ import annotations

from adapter.inbound.web.table_discovery_rule.dto import (
    CreateTableDiscoveryRuleApiRequest,
    TableDiscoveryRuleApiResponse,
    UpdateTableDiscoveryRuleApiRequest,
)
from adapter.inbound.web.table_discovery_rule.router import router

__all__ = [
    "CreateTableDiscoveryRuleApiRequest",
    "TableDiscoveryRuleApiResponse",
    "UpdateTableDiscoveryRuleApiRequest",
    "router",
]
