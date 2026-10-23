"""Delete a policy template that no rule references."""

from application.port.inbound.policy_template.delete_policy_template.input import (
    DeletePolicyTemplateUseCaseInput,
)
from application.port.inbound.policy_template.delete_policy_template.output import (
    DeletePolicyTemplateUseCaseOutput,
)
from application.port.inbound.policy_template.delete_policy_template.use_case import (
    DeletePolicyTemplateUseCase,
)

__all__ = [
    "DeletePolicyTemplateUseCase",
    "DeletePolicyTemplateUseCaseInput",
    "DeletePolicyTemplateUseCaseOutput",
]
