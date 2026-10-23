"""Define the CreatePolicyTemplateUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.policy_template.create_policy_template.input import (
    CreatePolicyTemplateUseCaseInput,
)
from application.port.inbound.policy_template.create_policy_template.output import (
    CreatePolicyTemplateUseCaseOutput,
)
from base.use_case import UseCase


class CreatePolicyTemplateUseCase(
    UseCase[CreatePolicyTemplateUseCaseInput, CreatePolicyTemplateUseCaseOutput]
):
    """Create a policy template."""

    @abstractmethod
    def execute(
        self, request: CreatePolicyTemplateUseCaseInput
    ) -> CreatePolicyTemplateUseCaseOutput:
        """Create a policy template."""
