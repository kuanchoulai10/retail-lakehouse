"""Define the ListTableMaintenancePolicyAttachmentsService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table_maintenance_policy import TableMaintenancePolicyName
from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table_maintenance_policy import (
    ListTableMaintenancePolicyAttachmentsUseCase,
    ListTableMaintenancePolicyAttachmentsUseCaseInput,
    ListTableMaintenancePolicyAttachmentsUseCaseOutput,
)
from context.table_maintenance.application.service.shared import target_in_catalog, translate_domain_errors

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.shared import PolicyPlacementsStore
    from context.table_maintenance.application.port.outbound.table import ReadTableMetadataGateway, TablesRepo
    from context.table_maintenance.application.port.outbound.table_maintenance_policy import (
        TableMaintenancePoliciesRepo,
    )


class ListTableMaintenancePolicyAttachmentsService(ListTableMaintenancePolicyAttachmentsUseCase):
    """List the places one maintenance policy is attached to, marking those that are gone."""

    def __init__(
        self,
        policies_repo: TableMaintenancePoliciesRepo,
        placements: PolicyPlacementsStore,
        gateway: ReadTableMetadataGateway,
        tables_repo: TablesRepo,
    ) -> None:
        """Bind the policies, the placements, the catalog gateway and the tables repo."""
        self._policies_repo = policies_repo
        self._placements = placements
        self._gateway = gateway
        self._tables_repo = tables_repo

    def execute(
        self, request: ListTableMaintenancePolicyAttachmentsUseCaseInput
    ) -> ListTableMaintenancePolicyAttachmentsUseCaseOutput:
        """Return the policy's places by type and then path, each orphaned when it no longer exists.

        An unknown policy is NotFoundError. A place in a catalog the platform's credential cannot read
        is not orphaned, and the listing still answers.
        """
        with translate_domain_errors():
            name = TableMaintenancePolicyName(value=request.policy_name)
        policy = self._policies_repo.get_by_name(name)
        if policy is None:
            raise NotFoundError(f"table maintenance policy {request.policy_name} not found")
        return ListTableMaintenancePolicyAttachmentsUseCaseOutput(
            items=tuple(
                ListTableMaintenancePolicyAttachmentsUseCaseOutput.Placement(
                    type=p.target.type.value,
                    path=p.target.path,
                    table_uuid=p.target.table_uuid,
                    policy_id=policy.id.value,
                    policy_name=policy.name.value,
                    orphaned=not target_in_catalog(p.target, self._gateway, self._tables_repo),
                )
                for p in self._placements.maintenance_placements(policy.id)
            )
        )
