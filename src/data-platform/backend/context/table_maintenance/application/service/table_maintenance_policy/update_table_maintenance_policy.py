"""Define the UpdateTableMaintenancePolicyService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    MaintenancePolicyContent,
    TableMaintenancePolicyName,
)
from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table_maintenance_policy import (
    UpdateTableMaintenancePolicyUseCase,
    UpdateTableMaintenancePolicyUseCaseInput,
    UpdateTableMaintenancePolicyUseCaseOutput,
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


class UpdateTableMaintenancePolicyService(UpdateTableMaintenancePolicyUseCase):
    """Replace a table maintenance policy's content as a new version."""

    def __init__(
        self,
        policies_repo: TableMaintenancePoliciesRepo,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Bind the repo and the clock."""
        self._policies_repo = policies_repo
        self._clock = clock

    def execute(self, request: UpdateTableMaintenancePolicyUseCaseInput) -> UpdateTableMaintenancePolicyUseCaseOutput:
        """Replace the content when ``version`` is the current one, else raise ConflictError."""
        with translate_domain_errors():
            name = TableMaintenancePolicyName(request.name)
            content = MaintenancePolicyContent.from_primitives(request.content)
        policy = self._policies_repo.get(name)
        if policy is None:
            raise NotFoundError(f"table maintenance policy {request.name} not found")
        with translate_domain_errors():
            policy.replace(content, request.version, self._clock())
            self._policies_repo.update(policy)
        return UpdateTableMaintenancePolicyUseCaseOutput(**table_maintenance_policy_output_fields(policy))
