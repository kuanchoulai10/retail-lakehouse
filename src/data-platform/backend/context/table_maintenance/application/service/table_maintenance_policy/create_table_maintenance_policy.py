"""Define the CreateTableMaintenancePolicyService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    MaintenancePolicyContent,
    TableMaintenancePolicy,
    TableMaintenancePolicyName,
)
from context.table_maintenance.application.exceptions import ConflictError
from context.table_maintenance.application.port.inbound.table_maintenance_policy import (
    CreateTableMaintenancePolicyUseCase,
    CreateTableMaintenancePolicyUseCaseInput,
    CreateTableMaintenancePolicyUseCaseOutput,
)
from context.table_maintenance.application.service.shared import (
    translate_domain_errors,
)
from context.table_maintenance.application.service.table_maintenance_policy.table_maintenance_policy_output_fields import (  # noqa: E501
    table_maintenance_policy_output_fields,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from context.table_maintenance.application.port.outbound.table_maintenance_policy import (
        TableMaintenancePoliciesRepo,
    )


class CreateTableMaintenancePolicyService(CreateTableMaintenancePolicyUseCase):
    """Create a table maintenance policy with a unique, well-formed name."""

    def __init__(
        self,
        policies_repo: TableMaintenancePoliciesRepo,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Bind the repo and the clock."""
        self._policies_repo = policies_repo
        self._clock = clock

    def execute(self, request: CreateTableMaintenancePolicyUseCaseInput) -> CreateTableMaintenancePolicyUseCaseOutput:
        """Create the policy at version 1, rejecting a bad name, bad content or a taken name."""
        with translate_domain_errors():
            name = TableMaintenancePolicyName(value=request.name)
            content = MaintenancePolicyContent.from_primitives(request.content)
        if self._policies_repo.get_by_name(name) is not None:
            raise ConflictError(f"policy name {name.value!r} already exists")
        policy = TableMaintenancePolicy.create(name, content, self._clock())
        self._policies_repo.create(policy)
        return CreateTableMaintenancePolicyUseCaseOutput(**table_maintenance_policy_output_fields(policy))
