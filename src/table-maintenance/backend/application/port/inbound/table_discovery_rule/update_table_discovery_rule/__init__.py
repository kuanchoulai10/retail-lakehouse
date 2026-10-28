"""Replace a discovery rule's definition."""

from application.port.inbound.table_discovery_rule.update_table_discovery_rule.input import (
    UpdateTableDiscoveryRuleUseCaseInput,
)
from application.port.inbound.table_discovery_rule.update_table_discovery_rule.output import (
    UpdateTableDiscoveryRuleUseCaseOutput,
)
from application.port.inbound.table_discovery_rule.update_table_discovery_rule.use_case import (
    UpdateTableDiscoveryRuleUseCase,
)

__all__ = [
    "UpdateTableDiscoveryRuleUseCase",
    "UpdateTableDiscoveryRuleUseCaseInput",
    "UpdateTableDiscoveryRuleUseCaseOutput",
]
