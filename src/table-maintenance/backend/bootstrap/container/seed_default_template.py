"""Provide the seed_default_template function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.port.inbound.policy_template.create_policy_template import (
    CreatePolicyTemplateUseCaseInput,
)
from application.port.inbound.policy_template.list_policy_templates import (
    ListPolicyTemplatesUseCaseInput,
)

if TYPE_CHECKING:
    from application.port.inbound.policy_template.create_policy_template import (
        CreatePolicyTemplateUseCase,
    )
    from application.port.inbound.policy_template.list_policy_templates import (
        ListPolicyTemplatesUseCase,
    )

DEFAULT_TEMPLATE_NAME = "default"


def seed_default_template(
    list_templates: ListPolicyTemplatesUseCase,
    create_template: CreatePolicyTemplateUseCase,
) -> bool:
    """Create the ``default`` template with default settings if none exists.

    Returns whether it created the template.
    """
    if list_templates.execute(ListPolicyTemplatesUseCaseInput()).items:
        return False
    create_template.execute(
        CreatePolicyTemplateUseCaseInput(name=DEFAULT_TEMPLATE_NAME)
    )
    return True
