"""Define the ListDiscoveryRulesService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.port.inbound.discovery_rule.list_discovery_rules import (
    ListDiscoveryRulesUseCase,
    ListDiscoveryRulesUseCaseInput,
    ListDiscoveryRulesUseCaseOutput,
    ListDiscoveryRulesUseCaseOutputItem,
)
from application.service.discovery_rule.discovery_rule_output_fields import (
    discovery_rule_output_fields,
)

if TYPE_CHECKING:
    from application.port.outbound.discovery_rule.discovery_rules_repo import (
        DiscoveryRulesRepo,
    )


class ListDiscoveryRulesService(ListDiscoveryRulesUseCase):
    """List all discovery rules."""

    def __init__(self, rules_repo: DiscoveryRulesRepo) -> None:
        """Bind the repo."""
        self._rules_repo = rules_repo

    def execute(
        self,
        request: ListDiscoveryRulesUseCaseInput,  # noqa: ARG002
    ) -> ListDiscoveryRulesUseCaseOutput:
        """Return every rule in priority order."""
        return ListDiscoveryRulesUseCaseOutput(
            items=[
                ListDiscoveryRulesUseCaseOutputItem(**discovery_rule_output_fields(r))
                for r in self._rules_repo.list_all()
            ]
        )
