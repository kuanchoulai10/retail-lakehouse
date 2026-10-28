"""Define the DeleteTableDiscoveryRuleService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.domain.model.table_discovery_rule.table_discovery_rule_id import (
    TableDiscoveryRuleId,
)
from application.exceptions import NotFoundError
from application.port.inbound.table_discovery_rule.delete_table_discovery_rule import (
    DeleteTableDiscoveryRuleUseCase,
    DeleteTableDiscoveryRuleUseCaseInput,
    DeleteTableDiscoveryRuleUseCaseOutput,
)

if TYPE_CHECKING:
    from application.port.outbound.table_discovery_rule.table_discovery_rules_repo import (
        TableDiscoveryRulesRepo,
    )


class DeleteTableDiscoveryRuleService(DeleteTableDiscoveryRuleUseCase):
    """Delete a discovery rule."""

    def __init__(self, rules_repo: TableDiscoveryRulesRepo) -> None:
        """Bind the repo."""
        self._rules_repo = rules_repo

    def execute(
        self, request: DeleteTableDiscoveryRuleUseCaseInput
    ) -> DeleteTableDiscoveryRuleUseCaseOutput:
        """Delete the rule or raise NotFoundError."""
        rule_id = TableDiscoveryRuleId(request.id)
        if self._rules_repo.get(rule_id) is None:
            raise NotFoundError(f"discovery rule {request.id} not found")
        self._rules_repo.delete(rule_id)
        return DeleteTableDiscoveryRuleUseCaseOutput()
