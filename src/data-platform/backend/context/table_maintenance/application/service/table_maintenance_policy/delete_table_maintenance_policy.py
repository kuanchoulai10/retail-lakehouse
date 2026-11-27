"""Define the DeleteTableMaintenancePolicyService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    TableMaintenancePolicyName,
)
from context.table_maintenance.application.exceptions import (
    ConflictError,
    NotFoundError,
)
from context.table_maintenance.application.port.inbound.table_maintenance_policy import (
    DeleteTableMaintenancePolicyUseCase,
    DeleteTableMaintenancePolicyUseCaseInput,
    DeleteTableMaintenancePolicyUseCaseOutput,
)
from context.table_maintenance.application.service.shared import (
    translate_domain_errors,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.shared import PolicyPlacementsStore
    from context.table_maintenance.application.port.outbound.table_maintenance_policy import (
        TableMaintenancePoliciesRepo,
    )


class DeleteTableMaintenancePolicyService(DeleteTableMaintenancePolicyUseCase):
    """Delete a table maintenance policy other than the default and not attached anywhere."""

    def __init__(self, policies_repo: TableMaintenancePoliciesRepo, placements: PolicyPlacementsStore) -> None:
        """Bind the policies and the placements."""
        self._policies_repo = policies_repo
        self._placements = placements

    def execute(self, request: DeleteTableMaintenancePolicyUseCaseInput) -> DeleteTableMaintenancePolicyUseCaseOutput:
        """Delete the policy and its versions, refusing the default and one still attached, with ConflictError.

        A policy still attached is refused naming each place as ``type:catalog.namespace.table``,
        comma-joined. A place attached between this check and the delete is refused by the repo
        (ConflictError).
        """
        with translate_domain_errors():
            name = TableMaintenancePolicyName(value=request.name)
        policy = self._policies_repo.get_by_name(name)
        if policy is None:
            raise NotFoundError(f"table maintenance policy {request.name} not found")
        if policy.is_default:
            raise ConflictError("the default policy cannot be deleted")
        placements = self._placements.maintenance_placements(policy.id)
        if placements:
            places = ", ".join(f"{p.target.type.value}:{'.'.join(p.target.path)}" for p in placements)
            raise ConflictError(f"maintenance policy {name.value} is still attached to {places}")
        self._policies_repo.delete(policy.id)
        return DeleteTableMaintenancePolicyUseCaseOutput()
