"""Define the CreateDiscoveryRuleService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from application.domain.model.discovery_rule.discovery_rule import DiscoveryRule
from application.domain.model.discovery_rule.discovery_rule_id import DiscoveryRuleId
from application.domain.model.discovery_rule.rule_effect import RuleEffect
from application.domain.model.discovery_rule.table_pattern import TablePattern
from application.domain.model.policy_template.policy_template_id import (
    PolicyTemplateId,
)
from application.exceptions import NotFoundError
from application.port.inbound.discovery_rule.create_discovery_rule import (
    CreateDiscoveryRuleUseCase,
    CreateDiscoveryRuleUseCaseInput,
    CreateDiscoveryRuleUseCaseOutput,
)
from application.service.discovery_rule.discovery_rule_output_fields import (
    discovery_rule_output_fields,
)
from application.service.translate_domain_errors import translate_domain_errors

if TYPE_CHECKING:
    from collections.abc import Callable

    from application.port.outbound.discovery_rule.discovery_rules_repo import (
        DiscoveryRulesRepo,
    )
    from application.port.outbound.policy_template.policy_templates_repo import (
        PolicyTemplatesRepo,
    )


class CreateDiscoveryRuleService(CreateDiscoveryRuleUseCase):
    """Create a discovery rule that points at an existing template."""

    def __init__(
        self,
        rules_repo: DiscoveryRulesRepo,
        templates_repo: PolicyTemplatesRepo,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        new_id: Callable[[], str] = lambda: str(uuid4()),
    ) -> None:
        """Bind the repos, the clock and the id generator."""
        self._rules_repo = rules_repo
        self._templates_repo = templates_repo
        self._clock = clock
        self._new_id = new_id

    def execute(
        self, request: CreateDiscoveryRuleUseCaseInput
    ) -> CreateDiscoveryRuleUseCaseOutput:
        """Create the rule after checking its template exists."""
        with translate_domain_errors():
            effect = RuleEffect(request.effect)
            template_id = (
                None
                if request.template_id is None
                else PolicyTemplateId(request.template_id)
            )
            if (
                template_id is not None
                and self._templates_repo.get(template_id) is None
            ):
                raise NotFoundError(f"policy template {template_id} not found")
            rule = DiscoveryRule.create(
                DiscoveryRuleId(self._new_id()),
                request.priority,
                effect,
                TablePattern(
                    request.catalog_pattern,
                    request.namespace_pattern,
                    request.table_pattern,
                ),
                template_id,
                request.enabled,
                self._clock(),
            )
            self._rules_repo.create(rule)
        return CreateDiscoveryRuleUseCaseOutput(**discovery_rule_output_fields(rule))
