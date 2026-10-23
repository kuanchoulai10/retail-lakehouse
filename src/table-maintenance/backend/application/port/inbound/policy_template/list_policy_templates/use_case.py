"""Define the ListPolicyTemplatesUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.policy_template.list_policy_templates.input import (
    ListPolicyTemplatesUseCaseInput,
)
from application.port.inbound.policy_template.list_policy_templates.output import (
    ListPolicyTemplatesUseCaseOutput,
)
from base.use_case import UseCase


class ListPolicyTemplatesUseCase(
    UseCase[ListPolicyTemplatesUseCaseInput, ListPolicyTemplatesUseCaseOutput]
):
    """List all policy templates."""

    @abstractmethod
    def execute(
        self, request: ListPolicyTemplatesUseCaseInput
    ) -> ListPolicyTemplatesUseCaseOutput:
        """List all policy templates."""
