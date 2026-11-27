"""Define the DeleteTableDiscoveryPolicyService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table_discovery_policy import (
    TableDiscoveryPolicyName,
)
from context.table_maintenance.application.exceptions import (
    ConflictError,
    NotFoundError,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy import (
    DeleteTableDiscoveryPolicyUseCase,
    DeleteTableDiscoveryPolicyUseCaseInput,
    DeleteTableDiscoveryPolicyUseCaseOutput,
)
from context.table_maintenance.application.service.shared import (
    translate_domain_errors,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.shared import PolicyPlacementsStore
    from context.table_maintenance.application.port.outbound.table_discovery_policy import (
        TableDiscoveryPoliciesRepo,
    )


class DeleteTableDiscoveryPolicyService(DeleteTableDiscoveryPolicyUseCase):
    """Delete a discovery policy that is not attached anywhere."""

    def __init__(self, policies_repo: TableDiscoveryPoliciesRepo, placements: PolicyPlacementsStore) -> None:
        """Bind the policies and the placements."""
        self._policies_repo = policies_repo
        self._placements = placements

    def execute(self, request: DeleteTableDiscoveryPolicyUseCaseInput) -> DeleteTableDiscoveryPolicyUseCaseOutput:
        """Delete the policy and its versions, refusing one still attached with ConflictError naming each place.

        Each place reads ``type:catalog.namespace.table``, comma-joined, so a policy on a table whose
        namespace has been dropped is refused just the same. A place attached between this check and the
        delete is refused by the repo (ConflictError).
        """
        with translate_domain_errors():
            name = TableDiscoveryPolicyName(value=request.name)
        policy = self._policies_repo.get_by_name(name)
        if policy is None:
            raise NotFoundError(f"discovery policy {request.name} not found")
        placements = self._placements.discovery_placements(policy.id)
        if placements:
            places = ", ".join(f"{p.target.type.value}:{'.'.join(p.target.path)}" for p in placements)
            raise ConflictError(f"discovery policy {name.value} is still attached to {places}")
        self._policies_repo.delete(policy.id)
        return DeleteTableDiscoveryPolicyUseCaseOutput()
