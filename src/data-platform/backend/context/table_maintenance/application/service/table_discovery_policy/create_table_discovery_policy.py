"""Define the CreateTableDiscoveryPolicyService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import TableDiscoveryRuleId
from context.table_maintenance.application.domain.model.table_discovery_policy import (
    DiscoveryPolicyContent,
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
from context.table_maintenance.application.service.table_discovery_policy.content_with_issued_rule_ids import (
    content_with_issued_rule_ids,
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
    """Create a discovery policy with a unique, well-formed name; every rule gets a new ``dr-`` id."""

    def __init__(
        self,
        policies_repo: TableDiscoveryPoliciesRepo,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        new_id: Callable[[], str] = lambda: TableDiscoveryRuleId.new().value,
    ) -> None:
        """Bind the repo, the clock and the rule id generator."""
        self._policies_repo = policies_repo
        self._clock = clock
        self._new_id = new_id

    def execute(self, request: CreateTableDiscoveryPolicyUseCaseInput) -> CreateTableDiscoveryPolicyUseCaseOutput:
        """Create the policy at version 1, rejecting a bad name, bad content, any rule id sent or a taken name."""
        with translate_domain_errors():
            name = TableDiscoveryPolicyName(value=request.name)
            primitives, new_ids = content_with_issued_rule_ids(request.content, self._new_id)
            content = DiscoveryPolicyContent.from_primitives(primitives)
            policy = TableDiscoveryPolicy.create(
                name, content, self._clock(), new_rule_ids={TableDiscoveryRuleId(i) for i in new_ids}
            )
        if self._policies_repo.get_by_name(name) is not None:
            raise ConflictError(f"discovery policy name {name.value!r} already exists")
        self._policies_repo.create(policy)
        return CreateTableDiscoveryPolicyUseCaseOutput(**table_discovery_policy_output_fields(policy))
