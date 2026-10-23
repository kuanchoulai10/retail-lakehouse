"""Define the GetPolicyTemplateUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.policy_template.get_policy_template.input import (
    GetPolicyTemplateUseCaseInput,
)
from application.port.inbound.policy_template.get_policy_template.output import (
    GetPolicyTemplateUseCaseOutput,
)
from base.use_case import UseCase


class GetPolicyTemplateUseCase(
    UseCase[GetPolicyTemplateUseCaseInput, GetPolicyTemplateUseCaseOutput]
):
    """Get one policy template."""

    @abstractmethod
    def execute(
        self, request: GetPolicyTemplateUseCaseInput
    ) -> GetPolicyTemplateUseCaseOutput:
        """Get one policy template."""
