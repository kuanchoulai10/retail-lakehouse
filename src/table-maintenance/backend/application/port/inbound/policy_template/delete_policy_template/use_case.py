"""Define the DeletePolicyTemplateUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.policy_template.delete_policy_template.input import (
    DeletePolicyTemplateUseCaseInput,
)
from application.port.inbound.policy_template.delete_policy_template.output import (
    DeletePolicyTemplateUseCaseOutput,
)
from base.use_case import UseCase


class DeletePolicyTemplateUseCase(
    UseCase[DeletePolicyTemplateUseCaseInput, DeletePolicyTemplateUseCaseOutput]
):
    """Delete a policy template that no rule references."""

    @abstractmethod
    def execute(
        self, request: DeletePolicyTemplateUseCaseInput
    ) -> DeletePolicyTemplateUseCaseOutput:
        """Delete a policy template that no rule references."""
