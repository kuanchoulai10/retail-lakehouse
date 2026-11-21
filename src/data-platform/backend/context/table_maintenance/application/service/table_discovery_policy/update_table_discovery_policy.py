"""Define the UpdateTableDiscoveryPolicyService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table_discovery_policy import (
    DiscoveryPolicyContent,
    TableDiscoveryPolicyName,
    TableDiscoveryRuleId,
)
from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table_discovery_policy import (
    UpdateTableDiscoveryPolicyUseCase,
    UpdateTableDiscoveryPolicyUseCaseInput,
    UpdateTableDiscoveryPolicyUseCaseOutput,
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


class UpdateTableDiscoveryPolicyService(UpdateTableDiscoveryPolicyUseCase):
    """Replace a discovery policy's content as a new version."""

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

    def execute(self, request: UpdateTableDiscoveryPolicyUseCaseInput) -> UpdateTableDiscoveryPolicyUseCaseOutput:
        """Replace the content when ``version`` is the current one.

        A rule sent without an id gets a new ``dr-`` id; a rule sent with one keeps it, and the id must
        be one the current version holds. Invalid content, an empty or unknown rule id raises
        ValidationError; the default, or a stale version (also one a concurrent writer made stale), raises
        ConflictError. Either way nothing is saved.
        """
        with translate_domain_errors():
            name = TableDiscoveryPolicyName(value=request.name)
            primitives, new_ids = content_with_issued_rule_ids(request.content, self._new_id)
            content = DiscoveryPolicyContent.from_primitives(primitives)
        policy = self._policies_repo.get_by_name(name)
        if policy is None:
            raise NotFoundError(f"discovery policy {request.name} not found")
        with translate_domain_errors():
            policy.replace(
                content,
                request.version,
                self._clock(),
                new_rule_ids={TableDiscoveryRuleId(i) for i in new_ids},
            )
            self._policies_repo.update(policy)
        return UpdateTableDiscoveryPolicyUseCaseOutput(**table_discovery_policy_output_fields(policy))
