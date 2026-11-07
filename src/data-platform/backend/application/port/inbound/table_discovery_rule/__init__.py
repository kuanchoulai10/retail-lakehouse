"""Inbound ports for the table_discovery_rule group."""

from __future__ import annotations

from application.port.inbound.table_discovery_rule.create_table_discovery_rule.input import (
    CreateTableDiscoveryRuleUseCaseInput,
)
from application.port.inbound.table_discovery_rule.create_table_discovery_rule.output import (
    CreateTableDiscoveryRuleUseCaseOutput,
)
from application.port.inbound.table_discovery_rule.create_table_discovery_rule.use_case import (
    CreateTableDiscoveryRuleUseCase,
)
from application.port.inbound.table_discovery_rule.delete_table_discovery_rule.input import (
    DeleteTableDiscoveryRuleUseCaseInput,
)
from application.port.inbound.table_discovery_rule.delete_table_discovery_rule.output import (
    DeleteTableDiscoveryRuleUseCaseOutput,
)
from application.port.inbound.table_discovery_rule.delete_table_discovery_rule.use_case import (
    DeleteTableDiscoveryRuleUseCase,
)
from application.port.inbound.table_discovery_rule.list_table_discovery_rules.input import (
    ListTableDiscoveryRulesUseCaseInput,
)
from application.port.inbound.table_discovery_rule.list_table_discovery_rules.output import (
    ListTableDiscoveryRulesUseCaseOutput,
    ListTableDiscoveryRulesUseCaseOutputItem,
)
from application.port.inbound.table_discovery_rule.list_table_discovery_rules.use_case import (
    ListTableDiscoveryRulesUseCase,
)
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
    "CreateTableDiscoveryRuleUseCase",
    "CreateTableDiscoveryRuleUseCaseInput",
    "CreateTableDiscoveryRuleUseCaseOutput",
    "DeleteTableDiscoveryRuleUseCase",
    "DeleteTableDiscoveryRuleUseCaseInput",
    "DeleteTableDiscoveryRuleUseCaseOutput",
    "ListTableDiscoveryRulesUseCase",
    "ListTableDiscoveryRulesUseCaseInput",
    "ListTableDiscoveryRulesUseCaseOutput",
    "ListTableDiscoveryRulesUseCaseOutputItem",
    "UpdateTableDiscoveryRuleUseCase",
    "UpdateTableDiscoveryRuleUseCaseInput",
    "UpdateTableDiscoveryRuleUseCaseOutput",
]
