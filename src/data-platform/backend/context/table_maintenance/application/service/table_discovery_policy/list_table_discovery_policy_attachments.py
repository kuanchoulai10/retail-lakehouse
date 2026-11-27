"""Define the ListTableDiscoveryPolicyAttachmentsService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table_discovery_policy import TableDiscoveryPolicyName
from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table_discovery_policy import (
    ListTableDiscoveryPolicyAttachmentsUseCase,
    ListTableDiscoveryPolicyAttachmentsUseCaseInput,
    ListTableDiscoveryPolicyAttachmentsUseCaseOutput,
)
from context.table_maintenance.application.service.shared import target_in_catalog, translate_domain_errors

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.shared import PolicyPlacementsStore
    from context.table_maintenance.application.port.outbound.table import ReadTableMetadataGateway, TablesRepo
    from context.table_maintenance.application.port.outbound.table_discovery_policy import (
        TableDiscoveryPoliciesRepo,
    )


class ListTableDiscoveryPolicyAttachmentsService(ListTableDiscoveryPolicyAttachmentsUseCase):
    """List the places one discovery policy is attached to, marking those that are gone."""

    def __init__(
        self,
        policies_repo: TableDiscoveryPoliciesRepo,
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
        self, request: ListTableDiscoveryPolicyAttachmentsUseCaseInput
    ) -> ListTableDiscoveryPolicyAttachmentsUseCaseOutput:
        """Return the policy's places by type and then path, each orphaned when it no longer exists.

        An unknown policy is NotFoundError. A place in a catalog the platform's credential cannot read
        is not orphaned, and the listing still answers.
        """
        with translate_domain_errors():
            name = TableDiscoveryPolicyName(value=request.policy_name)
        policy = self._policies_repo.get_by_name(name)
        if policy is None:
            raise NotFoundError(f"discovery policy {request.policy_name} not found")
        return ListTableDiscoveryPolicyAttachmentsUseCaseOutput(
            items=tuple(
                ListTableDiscoveryPolicyAttachmentsUseCaseOutput.Placement(
                    type=p.target.type.value,
                    path=p.target.path,
                    table_uuid=p.target.table_uuid,
                    policy_id=policy.id.value,
                    policy_name=policy.name.value,
                    orphaned=not target_in_catalog(p.target, self._gateway, self._tables_repo),
                )
                for p in self._placements.discovery_placements(policy.id)
            )
        )
