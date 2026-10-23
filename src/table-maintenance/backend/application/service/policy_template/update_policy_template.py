"""Define the UpdatePolicyTemplateService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from application.domain.model.policy_template.policy_template_id import (
    PolicyTemplateId,
)
from application.exceptions import ConflictError, NotFoundError, ValidationError
from application.port.inbound.policy_template.update_policy_template import (
    UpdatePolicyTemplateUseCase,
    UpdatePolicyTemplateUseCaseInput,
    UpdatePolicyTemplateUseCaseOutput,
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


class UpdatePolicyTemplateService(UpdatePolicyTemplateUseCase):
    """Rename a policy template and/or replace its settings."""

    def __init__(
        self,
        templates_repo: PolicyTemplatesRepo,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Bind the repo and the clock."""
        self._templates_repo = templates_repo
        self._clock = clock

    def execute(
        self, request: UpdatePolicyTemplateUseCaseInput
    ) -> UpdatePolicyTemplateUseCaseOutput:
        """Apply the given changes; omitted fields stay as they are."""
        template = self._templates_repo.get(PolicyTemplateId(request.id))
        if template is None:
            raise NotFoundError(f"policy template {request.id} not found")
        now = self._clock()
        settings = (
            None
            if request.settings is None
            else maintenance_settings_from_dict(request.settings)
        )
        if request.name is not None:
            name = request.name.strip()
            if not name:
                raise ValidationError("template name must not be blank")
            other = self._templates_repo.find_by_name(name)
            if other is not None and other.id != template.id:
                raise ConflictError(f"template name {name!r} already exists")
            template.rename(name, now)
        if settings is not None:
            template.update_settings(settings, now)
        self._templates_repo.update(template)
        return UpdatePolicyTemplateUseCaseOutput(
            **policy_template_output_fields(template)
        )
