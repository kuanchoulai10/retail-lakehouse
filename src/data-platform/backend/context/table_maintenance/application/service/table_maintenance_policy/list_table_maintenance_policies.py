"""Define the ListTableMaintenancePoliciesService."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from context.table_maintenance.application.port.inbound.table_maintenance_policy import (
    ListTableMaintenancePoliciesUseCase,
    ListTableMaintenancePoliciesUseCaseInput,
    ListTableMaintenancePoliciesUseCaseOutput,
    ListTableMaintenancePoliciesUseCaseOutputItem,
)
from context.table_maintenance.application.service.table_maintenance_policy.table_maintenance_policy_output_fields import (  # noqa: E501
    table_maintenance_policy_output_fields,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table_maintenance_policy import (
        TableMaintenancePoliciesRepo,
    )
    from context.table_maintenance.application.port.outbound.table_maintenance_policy_attachment import (
        TableMaintenancePolicyAttachmentsRepo,
    )


class ListTableMaintenancePoliciesService(ListTableMaintenancePoliciesUseCase):
    """List all table maintenance policies, each with how many targets it is attached to."""

    def __init__(
        self, policies_repo: TableMaintenancePoliciesRepo, attachments_repo: TableMaintenancePolicyAttachmentsRepo
    ) -> None:
        """Bind the repos."""
        self._policies_repo = policies_repo
        self._attachments_repo = attachments_repo

    def execute(
        self,
        request: ListTableMaintenancePoliciesUseCaseInput,  # noqa: ARG002
    ) -> ListTableMaintenancePoliciesUseCaseOutput:
        """Return every policy at its current version with its attachment count."""
        counts = Counter(a.policy_name.value for a in self._attachments_repo.list_all())
        return ListTableMaintenancePoliciesUseCaseOutput(
            items=[
                ListTableMaintenancePoliciesUseCaseOutputItem(
                    **table_maintenance_policy_output_fields(p), attachment_count=counts[p.id.value]
                )
                for p in self._policies_repo.list_all()
            ]
        )
