"""Define the CreateTableDiscoveryRuleService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from context.table_maintenance.application.domain.model.table_discovery_rule import (
    RuleEffect,
    TableDiscoveryRule,
    TableDiscoveryRuleId,
    TablePattern,
)
from context.table_maintenance.application.port.inbound.table_discovery_rule import (
    CreateTableDiscoveryRuleUseCase,
    CreateTableDiscoveryRuleUseCaseInput,
    CreateTableDiscoveryRuleUseCaseOutput,
)
from context.table_maintenance.application.service.shared import translate_domain_errors
from context.table_maintenance.application.service.table_discovery_rule.table_discovery_rule_output_fields import (
    table_discovery_rule_output_fields,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from context.table_maintenance.application.port.outbound.table_discovery_rule import (
        TableDiscoveryRulesRepo,
    )


class CreateTableDiscoveryRuleService(CreateTableDiscoveryRuleUseCase):
    """Create a discovery rule."""

    def __init__(
        self,
        rules_repo: TableDiscoveryRulesRepo,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        new_id: Callable[[], str] = lambda: str(uuid4()),
    ) -> None:
        """Bind the repo, the clock and the id generator."""
        self._rules_repo = rules_repo
        self._clock = clock
        self._new_id = new_id

    def execute(self, request: CreateTableDiscoveryRuleUseCaseInput) -> CreateTableDiscoveryRuleUseCaseOutput:
        """Create the rule."""
        with translate_domain_errors():
            effect = RuleEffect(request.effect)
            rule = TableDiscoveryRule.create(
                TableDiscoveryRuleId(self._new_id()),
                request.priority,
                effect,
                TablePattern(
                    catalog=request.catalog_pattern,
                    namespace=request.namespace_pattern,
                    table=request.table_pattern,
                ),
                request.enabled,
                self._clock(),
            )
            self._rules_repo.create(rule)
        return CreateTableDiscoveryRuleUseCaseOutput(**table_discovery_rule_output_fields(rule))
