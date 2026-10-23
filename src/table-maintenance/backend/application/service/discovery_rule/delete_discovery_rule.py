"""Define the DeleteDiscoveryRuleService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.domain.model.discovery_rule.discovery_rule_id import DiscoveryRuleId
from application.exceptions import NotFoundError
from application.port.inbound.discovery_rule.delete_discovery_rule import (
    DeleteDiscoveryRuleUseCase,
    DeleteDiscoveryRuleUseCaseInput,
    DeleteDiscoveryRuleUseCaseOutput,
)

if TYPE_CHECKING:
    from application.port.outbound.discovery_rule.discovery_rules_repo import (
        DiscoveryRulesRepo,
    )


class DeleteDiscoveryRuleService(DeleteDiscoveryRuleUseCase):
    """Delete a discovery rule."""

    def __init__(self, rules_repo: DiscoveryRulesRepo) -> None:
        """Bind the repo."""
        self._rules_repo = rules_repo

    def execute(
        self, request: DeleteDiscoveryRuleUseCaseInput
    ) -> DeleteDiscoveryRuleUseCaseOutput:
        """Delete the rule or raise NotFoundError."""
        rule_id = DiscoveryRuleId(request.id)
        if self._rules_repo.get(rule_id) is None:
            raise NotFoundError(f"discovery rule {request.id} not found")
        self._rules_repo.delete(rule_id)
        return DeleteDiscoveryRuleUseCaseOutput()
