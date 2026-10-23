"""Define the ListPolicyTemplatesService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.port.inbound.policy_template.list_policy_templates import (
    ListPolicyTemplatesUseCase,
    ListPolicyTemplatesUseCaseInput,
    ListPolicyTemplatesUseCaseOutput,
    ListPolicyTemplatesUseCaseOutputItem,
)
from application.service.policy_template.policy_template_output_fields import (
    policy_template_output_fields,
)

if TYPE_CHECKING:
    from application.port.outbound.policy_template.policy_templates_repo import (
        PolicyTemplatesRepo,
    )


class ListPolicyTemplatesService(ListPolicyTemplatesUseCase):
    """List all policy templates."""

    def __init__(self, templates_repo: PolicyTemplatesRepo) -> None:
        """Bind the repo."""
        self._templates_repo = templates_repo

    def execute(
        self,
        request: ListPolicyTemplatesUseCaseInput,  # noqa: ARG002
    ) -> ListPolicyTemplatesUseCaseOutput:
        """Return every template."""
        return ListPolicyTemplatesUseCaseOutput(
            items=[
                ListPolicyTemplatesUseCaseOutputItem(**policy_template_output_fields(t))
                for t in self._templates_repo.list_all()
            ]
        )
