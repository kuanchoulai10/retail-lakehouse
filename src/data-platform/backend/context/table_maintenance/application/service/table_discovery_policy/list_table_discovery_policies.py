"""Define the ListTableDiscoveryPoliciesService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.port.inbound.table_discovery_policy import (
    ListTableDiscoveryPoliciesUseCase,
    ListTableDiscoveryPoliciesUseCaseInput,
    ListTableDiscoveryPoliciesUseCaseOutput,
)
from context.table_maintenance.application.service.table_discovery_policy.table_discovery_policy_output_fields import (  # noqa: E501
    table_discovery_policy_output_fields,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.shared import PolicyPlacementsStore
    from context.table_maintenance.application.port.outbound.table_discovery_policy import (
        TableDiscoveryPoliciesRepo,
    )


class ListTableDiscoveryPoliciesService(ListTableDiscoveryPoliciesUseCase):
    """List all discovery policies, each with how many places it is attached to."""

    def __init__(self, policies_repo: TableDiscoveryPoliciesRepo, placements: PolicyPlacementsStore) -> None:
        """Bind the policies and the placements."""
        self._policies_repo = policies_repo
        self._placements = placements

    def execute(
        self,
        request: ListTableDiscoveryPoliciesUseCaseInput,  # noqa: ARG002
    ) -> ListTableDiscoveryPoliciesUseCaseOutput:
        """Return every policy at its current version with the number of places it is attached to, by name."""
        policies = sorted(self._policies_repo.list_all(), key=lambda p: p.name.value)
        return ListTableDiscoveryPoliciesUseCaseOutput(
            items=tuple(
                ListTableDiscoveryPoliciesUseCaseOutput.TableDiscoveryPolicy(
                    **table_discovery_policy_output_fields(p),
                    attachment_count=len(self._placements.discovery_placements(p.id)),
                )
                for p in policies
            )
        )
