"""Rename a policy template or replace its settings."""

from application.port.inbound.policy_template.update_policy_template.input import (
    UpdatePolicyTemplateUseCaseInput,
)
from application.port.inbound.policy_template.update_policy_template.output import (
    UpdatePolicyTemplateUseCaseOutput,
)
from application.port.inbound.policy_template.update_policy_template.use_case import (
    UpdatePolicyTemplateUseCase,
)

__all__ = [
    "UpdatePolicyTemplateUseCase",
    "UpdatePolicyTemplateUseCaseInput",
    "UpdatePolicyTemplateUseCaseOutput",
]
