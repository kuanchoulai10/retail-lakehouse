"""Inbound ports for the table_discovery_rules group."""

from __future__ import annotations

from context.table_maintenance.application.port.inbound.table_discovery_rules.get_table_discovery_rules.input import (
    GetTableDiscoveryRulesUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_discovery_rules.get_table_discovery_rules.output import (
    GetTableDiscoveryRulesUseCaseOutput,
)
from context.table_maintenance.application.port.inbound.table_discovery_rules.get_table_discovery_rules.use_case import (  # noqa: E501
    GetTableDiscoveryRulesUseCase,
)
from context.table_maintenance.application.port.inbound.table_discovery_rules.list_covered_catalogs.input import (
    ListCoveredCatalogsUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_discovery_rules.list_covered_catalogs.output import (
    ListCoveredCatalogsUseCaseOutput,
)
from context.table_maintenance.application.port.inbound.table_discovery_rules.list_covered_catalogs.use_case import (
    ListCoveredCatalogsUseCase,
)
from context.table_maintenance.application.port.inbound.table_discovery_rules.replace_table_discovery_rules.input import (  # noqa: E501
    ReplaceTableDiscoveryRulesUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_discovery_rules.replace_table_discovery_rules.output import (  # noqa: E501
    ReplaceTableDiscoveryRulesUseCaseOutput,
)
from context.table_maintenance.application.port.inbound.table_discovery_rules.replace_table_discovery_rules.use_case import (  # noqa: E501
    ReplaceTableDiscoveryRulesUseCase,
)

__all__ = [
    "GetTableDiscoveryRulesUseCase",
    "GetTableDiscoveryRulesUseCaseInput",
    "GetTableDiscoveryRulesUseCaseOutput",
    "ListCoveredCatalogsUseCase",
    "ListCoveredCatalogsUseCaseInput",
    "ListCoveredCatalogsUseCaseOutput",
    "ReplaceTableDiscoveryRulesUseCase",
    "ReplaceTableDiscoveryRulesUseCaseInput",
    "ReplaceTableDiscoveryRulesUseCaseOutput",
]
