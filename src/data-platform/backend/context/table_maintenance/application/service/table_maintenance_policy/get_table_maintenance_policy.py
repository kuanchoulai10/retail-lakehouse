"""Define the GetTableMaintenancePolicyService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    TableMaintenancePolicyName,
)
from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table_maintenance_policy import (
    GetTableMaintenancePolicyUseCase,
    GetTableMaintenancePolicyUseCaseInput,
    GetTableMaintenancePolicyUseCaseOutput,
)
from context.table_maintenance.application.service.shared import (
    translate_domain_errors,
)
from context.table_maintenance.application.service.table_maintenance_policy.table_maintenance_policy_output_fields import (  # noqa: E501
    table_maintenance_policy_output_fields,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table_maintenance_policy import (
        TableMaintenancePoliciesRepo,
    )


class GetTableMaintenancePolicyService(GetTableMaintenancePolicyUseCase):
    """Get the current version of one table maintenance policy."""

    def __init__(self, policies_repo: TableMaintenancePoliciesRepo) -> None:
        """Bind the repo."""
        self._policies_repo = policies_repo

    def execute(self, request: GetTableMaintenancePolicyUseCaseInput) -> GetTableMaintenancePolicyUseCaseOutput:
        """Return the policy or raise NotFoundError."""
        with translate_domain_errors():
            name = TableMaintenancePolicyName(value=request.name)
        policy = self._policies_repo.get_by_name(name)
        if policy is None:
            raise NotFoundError(f"table maintenance policy {request.name} not found")
        return GetTableMaintenancePolicyUseCaseOutput(**table_maintenance_policy_output_fields(policy))
