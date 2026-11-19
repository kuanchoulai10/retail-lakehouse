"""Define the GetTableMaintenancePolicyVersionService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    TableMaintenancePolicyName,
)
from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table_maintenance_policy import (
    GetTableMaintenancePolicyVersionUseCase,
    GetTableMaintenancePolicyVersionUseCaseInput,
    GetTableMaintenancePolicyVersionUseCaseOutput,
)
from context.table_maintenance.application.service.shared import (
    translate_domain_errors,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table_maintenance_policy import (
        TableMaintenancePoliciesRepo,
    )


class GetTableMaintenancePolicyVersionService(GetTableMaintenancePolicyVersionUseCase):
    """Get one stored version of a table maintenance policy."""

    def __init__(self, policies_repo: TableMaintenancePoliciesRepo) -> None:
        """Bind the repo."""
        self._policies_repo = policies_repo

    def execute(
        self, request: GetTableMaintenancePolicyVersionUseCaseInput
    ) -> GetTableMaintenancePolicyVersionUseCaseOutput:
        """Return the version or raise NotFoundError."""
        with translate_domain_errors():
            name = TableMaintenancePolicyName(value=request.name)
        policy = self._policies_repo.get_by_name(name)
        version = None if policy is None else self._policies_repo.get_version(policy.id, request.version)
        if policy is None or version is None:
            raise NotFoundError(f"table maintenance policy {request.name} has no version {request.version}")
        return GetTableMaintenancePolicyVersionUseCaseOutput(
            id=policy.id.value,
            name=policy.name.value,
            version=version.version,
            content=version.content.to_primitives(),
            created_at=version.created_at,
        )
