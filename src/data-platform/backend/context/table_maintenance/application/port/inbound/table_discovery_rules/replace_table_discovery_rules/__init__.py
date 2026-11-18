"""Replace the whole discovery rule list from the version read, then discover tables."""

from __future__ import annotations

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
    "ReplaceTableDiscoveryRulesUseCase",
    "ReplaceTableDiscoveryRulesUseCaseInput",
    "ReplaceTableDiscoveryRulesUseCaseOutput",
]
