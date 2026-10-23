"""Define the DeletePolicyTemplateService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.domain.model.policy_template.policy_template_id import (
    PolicyTemplateId,
)
from application.exceptions import ConflictError, NotFoundError
from application.port.inbound.policy_template.delete_policy_template import (
    DeletePolicyTemplateUseCase,
    DeletePolicyTemplateUseCaseInput,
    DeletePolicyTemplateUseCaseOutput,
)

if TYPE_CHECKING:
    from application.port.outbound.discovery_rule.discovery_rules_repo import (
        DiscoveryRulesRepo,
    )
    from application.port.outbound.policy_template.policy_templates_repo import (
        PolicyTemplatesRepo,
    )


class DeletePolicyTemplateService(DeletePolicyTemplateUseCase):
    """Delete a policy template that no discovery rule references."""

    def __init__(
        self, templates_repo: PolicyTemplatesRepo, rules_repo: DiscoveryRulesRepo
    ) -> None:
        """Bind the template and rule repos."""
        self._templates_repo = templates_repo
        self._rules_repo = rules_repo

    def execute(
        self, request: DeletePolicyTemplateUseCaseInput
    ) -> DeletePolicyTemplateUseCaseOutput:
        """Delete the template unless a rule still uses it."""
        template_id = PolicyTemplateId(request.id)
        if self._templates_repo.get(template_id) is None:
            raise NotFoundError(f"policy template {request.id} not found")
        if self._rules_repo.count_by_template(template_id) > 0:
            raise ConflictError(
                f"policy template {request.id} is referenced by discovery rules"
            )
        self._templates_repo.delete(template_id)
        return DeletePolicyTemplateUseCaseOutput()
