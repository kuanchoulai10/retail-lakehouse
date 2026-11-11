"""Define the ListTableMaintenancePoliciesService."""

from __future__ import annotations

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


class ListTableMaintenancePoliciesService(ListTableMaintenancePoliciesUseCase):
    """List all table maintenance policies."""

    def __init__(self, policies_repo: TableMaintenancePoliciesRepo) -> None:
        """Bind the repo."""
        self._policies_repo = policies_repo

    def execute(
        self,
        request: ListTableMaintenancePoliciesUseCaseInput,  # noqa: ARG002
    ) -> ListTableMaintenancePoliciesUseCaseOutput:
        """Return every policy at its current version."""
        return ListTableMaintenancePoliciesUseCaseOutput(
            items=[
                ListTableMaintenancePoliciesUseCaseOutputItem(**table_maintenance_policy_output_fields(p))
                for p in self._policies_repo.list_all()
            ]
        )
