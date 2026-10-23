"""Define the GetPolicyTemplateService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.domain.model.policy_template.policy_template_id import (
    PolicyTemplateId,
)
from application.exceptions import NotFoundError
from application.port.inbound.policy_template.get_policy_template import (
    GetPolicyTemplateUseCase,
    GetPolicyTemplateUseCaseInput,
    GetPolicyTemplateUseCaseOutput,
)
from application.service.policy_template.policy_template_output_fields import (
    policy_template_output_fields,
)

if TYPE_CHECKING:
    from application.port.outbound.policy_template.policy_templates_repo import (
        PolicyTemplatesRepo,
    )


class GetPolicyTemplateService(GetPolicyTemplateUseCase):
    """Get one policy template."""

    def __init__(self, templates_repo: PolicyTemplatesRepo) -> None:
        """Bind the repo."""
        self._templates_repo = templates_repo

    def execute(
        self, request: GetPolicyTemplateUseCaseInput
    ) -> GetPolicyTemplateUseCaseOutput:
        """Return the template or raise NotFoundError."""
        template = self._templates_repo.get(PolicyTemplateId(request.id))
        if template is None:
            raise NotFoundError(f"policy template {request.id} not found")
        return GetPolicyTemplateUseCaseOutput(**policy_template_output_fields(template))
