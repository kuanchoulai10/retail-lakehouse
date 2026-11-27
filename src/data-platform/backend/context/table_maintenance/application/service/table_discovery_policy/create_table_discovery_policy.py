"""Define the CreateTableDiscoveryPolicyService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table_discovery_policy import (
    TableDiscoveryPolicy,
    TableDiscoveryPolicyName,
)
from context.table_maintenance.application.exceptions import ConflictError
from context.table_maintenance.application.port.inbound.table_discovery_policy import (
    CreateTableDiscoveryPolicyUseCase,
    CreateTableDiscoveryPolicyUseCaseInput,
    CreateTableDiscoveryPolicyUseCaseOutput,
)
from context.table_maintenance.application.service.shared import (
    translate_domain_errors,
)
from context.table_maintenance.application.service.table_discovery_policy.discovery_rules_of import (
    discovery_rules_of,
)
from context.table_maintenance.application.service.table_discovery_policy.table_discovery_policy_output_fields import (  # noqa: E501
    table_discovery_policy_output_fields,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from context.table_maintenance.application.port.outbound.table_discovery_policy import (
        TableDiscoveryPoliciesRepo,
    )


class CreateTableDiscoveryPolicyService(CreateTableDiscoveryPolicyUseCase):
    """Create a discovery policy with a unique, well-formed name and at least one include or exclude rule."""

    def __init__(
        self,
        policies_repo: TableDiscoveryPoliciesRepo,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Bind the repo and the clock."""
        self._policies_repo = policies_repo
        self._clock = clock

    def execute(self, request: CreateTableDiscoveryPolicyUseCaseInput) -> CreateTableDiscoveryPolicyUseCaseOutput:
        """Create the policy at version 1, rejecting a bad name, bad rules or a taken name."""
        with translate_domain_errors():
            name = TableDiscoveryPolicyName(value=request.name)
            policy = TableDiscoveryPolicy.create(
                name, request.description, discovery_rules_of(request.rules), self._clock()
            )
        if self._policies_repo.get_by_name(name) is not None:
            raise ConflictError(f"discovery policy name {name.value!r} already exists")
        self._policies_repo.create(policy)
        return CreateTableDiscoveryPolicyUseCaseOutput(**table_discovery_policy_output_fields(policy))
