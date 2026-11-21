"""Define the EnsureDefaultTableDiscoveryPolicyService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table_discovery_policy import (
    DEFAULT_DISCOVERY_POLICY_ID,
    TableDiscoveryPolicy,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy import (
    EnsureDefaultTableDiscoveryPolicyUseCase,
    EnsureDefaultTableDiscoveryPolicyUseCaseInput,
    EnsureDefaultTableDiscoveryPolicyUseCaseOutput,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from context.table_maintenance.application.port.outbound.table_discovery_policy import (
        TableDiscoveryPoliciesRepo,
    )


class EnsureDefaultTableDiscoveryPolicyService(EnsureDefaultTableDiscoveryPolicyUseCase):
    """Create the default table discovery policy when it is missing."""

    def __init__(
        self,
        policies_repo: TableDiscoveryPoliciesRepo,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Bind the repo and the clock."""
        self._policies_repo = policies_repo
        self._clock = clock

    def execute(
        self,
        request: EnsureDefaultTableDiscoveryPolicyUseCaseInput,  # noqa: ARG002
    ) -> EnsureDefaultTableDiscoveryPolicyUseCaseOutput:
        """Create ``default`` under its fixed id with the platform default content unless that id exists."""
        if self._policies_repo.get(DEFAULT_DISCOVERY_POLICY_ID) is not None:
            return EnsureDefaultTableDiscoveryPolicyUseCaseOutput(created=False)
        self._policies_repo.create(TableDiscoveryPolicy.create_default(self._clock()))
        return EnsureDefaultTableDiscoveryPolicyUseCaseOutput(created=True)
