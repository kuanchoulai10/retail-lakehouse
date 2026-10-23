"""Define the UpdatePolicyTemplateUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.policy_template.update_policy_template.input import (
    UpdatePolicyTemplateUseCaseInput,
)
from application.port.inbound.policy_template.update_policy_template.output import (
    UpdatePolicyTemplateUseCaseOutput,
)
from base.use_case import UseCase


class UpdatePolicyTemplateUseCase(
    UseCase[UpdatePolicyTemplateUseCaseInput, UpdatePolicyTemplateUseCaseOutput]
):
    """Rename a policy template or replace its settings."""

    @abstractmethod
    def execute(
        self, request: UpdatePolicyTemplateUseCaseInput
    ) -> UpdatePolicyTemplateUseCaseOutput:
        """Rename a policy template or replace its settings."""
