"""Define the DeleteTableMaintenancePolicyService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    DEFAULT_POLICY_NAME,
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
    from context.table_maintenance.application.port.outbound.table_maintenance_policy import (
        TableMaintenancePoliciesRepo,
    )


class DeleteTableMaintenancePolicyService(DeleteTableMaintenancePolicyUseCase):
    """Delete a table maintenance policy other than the default."""

    def __init__(self, policies_repo: TableMaintenancePoliciesRepo) -> None:
        """Bind the repo."""
        self._policies_repo = policies_repo

    def execute(self, request: DeleteTableMaintenancePolicyUseCaseInput) -> DeleteTableMaintenancePolicyUseCaseOutput:
        """Delete the policy, refusing the default one."""
        with translate_domain_errors():
            name = TableMaintenancePolicyName(request.name)
        if self._policies_repo.get(name) is None:
            raise NotFoundError(f"table maintenance policy {request.name} not found")
        if name.value == DEFAULT_POLICY_NAME:
            raise ConflictError("the default policy cannot be deleted")
        self._policies_repo.delete(name)
        return DeleteTableMaintenancePolicyUseCaseOutput()
