"""Define the ListTableMaintenancePoliciesService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.port.inbound.table_maintenance_policy import (
    ListTableMaintenancePoliciesUseCase,
    ListTableMaintenancePoliciesUseCaseInput,
    ListTableMaintenancePoliciesUseCaseOutput,
)
from context.table_maintenance.application.service.table_maintenance_policy.table_maintenance_policy_output_fields import (  # noqa: E501
    table_maintenance_policy_output_fields,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.shared import PolicyPlacementsStore
    from context.table_maintenance.application.port.outbound.table_maintenance_policy import (
        TableMaintenancePoliciesRepo,
    )


class ListTableMaintenancePoliciesService(ListTableMaintenancePoliciesUseCase):
    """List all table maintenance policies, each with how many places it is attached to."""

    def __init__(self, policies_repo: TableMaintenancePoliciesRepo, placements: PolicyPlacementsStore) -> None:
        """Bind the policies and the placements."""
        self._policies_repo = policies_repo
        self._placements = placements

    def execute(
        self,
        request: ListTableMaintenancePoliciesUseCaseInput,  # noqa: ARG002
    ) -> ListTableMaintenancePoliciesUseCaseOutput:
        """Return every policy at its current version with the number of places it is attached to."""
        return ListTableMaintenancePoliciesUseCaseOutput(
            items=tuple(
                ListTableMaintenancePoliciesUseCaseOutput.TableMaintenancePolicy(
                    **table_maintenance_policy_output_fields(p),
                    attachment_count=len(self._placements.maintenance_placements(p.id)),
                )
                for p in self._policies_repo.list_all()
            )
        )
