"""Define the EnsureDefaultTableMaintenancePolicyService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    DEFAULT_POLICY_NAME,
    MaintenancePolicyContent,
    TableMaintenancePolicy,
    TableMaintenancePolicyName,
)
from context.table_maintenance.application.port.inbound.table_maintenance_policy import (
    EnsureDefaultTableMaintenancePolicyUseCase,
    EnsureDefaultTableMaintenancePolicyUseCaseInput,
    EnsureDefaultTableMaintenancePolicyUseCaseOutput,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from context.table_maintenance.application.port.outbound.table_maintenance_policy import (
        TableMaintenancePoliciesRepo,
    )


class EnsureDefaultTableMaintenancePolicyService(EnsureDefaultTableMaintenancePolicyUseCase):
    """Create the default table maintenance policy when it is missing."""

    def __init__(
        self,
        policies_repo: TableMaintenancePoliciesRepo,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Bind the repo and the clock."""
        self._policies_repo = policies_repo
        self._clock = clock

    def execute(
        self,
        request: EnsureDefaultTableMaintenancePolicyUseCaseInput,  # noqa: ARG002
    ) -> EnsureDefaultTableMaintenancePolicyUseCaseOutput:
        """Create ``default`` with the platform default content unless it exists."""
        name = TableMaintenancePolicyName(DEFAULT_POLICY_NAME)
        if self._policies_repo.get(name) is not None:
            return EnsureDefaultTableMaintenancePolicyUseCaseOutput(created=False)
        policy = TableMaintenancePolicy.create(name, MaintenancePolicyContent.platform_default(), self._clock())
        self._policies_repo.create(policy)
        return EnsureDefaultTableMaintenancePolicyUseCaseOutput(created=True)
