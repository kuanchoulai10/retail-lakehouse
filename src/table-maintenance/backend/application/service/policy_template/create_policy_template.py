"""Define the CreatePolicyTemplateService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from application.domain.model.policy_template.policy_template import PolicyTemplate
from application.domain.model.policy_template.policy_template_id import (
    PolicyTemplateId,
)
from application.exceptions import ConflictError, ValidationError
from application.port.inbound.policy_template.create_policy_template import (
    CreatePolicyTemplateUseCase,
    CreatePolicyTemplateUseCaseInput,
    CreatePolicyTemplateUseCaseOutput,
)
from application.service.maintenance_settings.maintenance_settings_from_dict import (
    maintenance_settings_from_dict,
)
from application.service.policy_template.policy_template_output_fields import (
    policy_template_output_fields,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from application.port.outbound.policy_template.policy_templates_repo import (
        PolicyTemplatesRepo,
    )


class CreatePolicyTemplateService(CreatePolicyTemplateUseCase):
    """Create a policy template with a unique name."""

    def __init__(
        self,
        templates_repo: PolicyTemplatesRepo,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        new_id: Callable[[], str] = lambda: str(uuid4()),
    ) -> None:
        """Bind the repo, the clock and the id generator."""
        self._templates_repo = templates_repo
        self._clock = clock
        self._new_id = new_id

    def execute(
        self, request: CreatePolicyTemplateUseCaseInput
    ) -> CreatePolicyTemplateUseCaseOutput:
        """Create the template, rejecting a blank or taken name."""
        name = request.name.strip()
        if not name:
            raise ValidationError("template name must not be blank")
        settings = maintenance_settings_from_dict(request.settings)
        if self._templates_repo.find_by_name(name) is not None:
            raise ConflictError(f"template name {name!r} already exists")
        template = PolicyTemplate.create(
            PolicyTemplateId(self._new_id()), name, settings, self._clock()
        )
        self._templates_repo.create(template)
        return CreatePolicyTemplateUseCaseOutput(
            **policy_template_output_fields(template)
        )
