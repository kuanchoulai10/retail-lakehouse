"""Define the EnsureDefaultTableMaintenancePolicyService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    DEFAULT_POLICY_ID,
    TableMaintenancePolicy,
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
        """Create ``default`` under its fixed id with the platform default content unless that id exists."""
        if self._policies_repo.get(DEFAULT_POLICY_ID) is not None:
            return EnsureDefaultTableMaintenancePolicyUseCaseOutput(created=False)
        self._policies_repo.create(TableMaintenancePolicy.create_default(self._clock()))
        return EnsureDefaultTableMaintenancePolicyUseCaseOutput(created=True)
