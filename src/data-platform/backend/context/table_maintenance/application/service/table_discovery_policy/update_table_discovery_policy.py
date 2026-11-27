"""Define the UpdateTableDiscoveryPolicyService."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import PolicyTarget, PolicyTargetType
from context.table_maintenance.application.domain.model.table_discovery_policy import TableDiscoveryPolicyName
from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table_discovery_policy import (
    UpdateTableDiscoveryPolicyUseCase,
    UpdateTableDiscoveryPolicyUseCaseInput,
    UpdateTableDiscoveryPolicyUseCaseOutput,
)
from context.table_maintenance.application.service.shared import (
    translate_domain_errors,
)
from context.table_maintenance.application.service.table_discovery_policy.discovery_rules_of import (
    discovery_rules_of,
)
from context.table_maintenance.application.service.table_discovery_policy.request_discovery_scan import (
    request_discovery_scan,
)
from context.table_maintenance.application.service.table_discovery_policy.table_discovery_policy_output_fields import (  # noqa: E501
    table_discovery_policy_output_fields,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from context.table_maintenance.application.port.outbound.shared import PolicyPlacementsStore
    from context.table_maintenance.application.port.outbound.table import SendDiscoveryRequestGateway
    from context.table_maintenance.application.port.outbound.table_discovery_policy import (
        TableDiscoveryPoliciesRepo,
    )


class UpdateTableDiscoveryPolicyService(UpdateTableDiscoveryPolicyUseCase):
    """Revise a discovery policy's description and rules as a new version."""

    def __init__(
        self,
        policies_repo: TableDiscoveryPoliciesRepo,
        placements: PolicyPlacementsStore,
        discovery_requests: SendDiscoveryRequestGateway,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        new_change_id: Callable[[], str] = lambda: uuid.uuid4().hex,
    ) -> None:
        """Bind the policies, the placements, the discovery requests, the clock and the change id generator."""
        self._policies_repo = policies_repo
        self._placements = placements
        self._discovery_requests = discovery_requests
        self._clock = clock
        self._new_change_id = new_change_id

    def execute(self, request: UpdateTableDiscoveryPolicyUseCaseInput) -> UpdateTableDiscoveryPolicyUseCaseOutput:
        """Replace the description and the rules when ``version`` is the current one.

        Bad rules (none, an unknown action, an empty pattern, a missing or unknown field) raise
        ValidationError; a stale version (also one a concurrent writer made stale) raises ConflictError.
        Either way nothing is saved or scanned. Once saved, every catalog the policy is attached in (to
        the catalog, a namespace or a table of it) is scanned whole, once, under one new change id, best
        effort: a request that cannot be sent is logged, and the revision stands.
        """
        with translate_domain_errors():
            name = TableDiscoveryPolicyName(value=request.name)
            rules = discovery_rules_of(request.rules)
        policy = self._policies_repo.get_by_name(name)
        if policy is None:
            raise NotFoundError(f"discovery policy {request.name} not found")
        with translate_domain_errors():
            policy.revise(request.description, rules, request.version, self._clock())
            self._policies_repo.update(policy)
        catalogs = sorted({p.target.path[0] for p in self._placements.discovery_placements(policy.id)})
        change_id = self._new_change_id()
        for catalog in catalogs:
            target = PolicyTarget(type=PolicyTargetType.CATALOG, path=(catalog,))
            request_discovery_scan(self._discovery_requests, target, change_id=change_id)
        return UpdateTableDiscoveryPolicyUseCaseOutput(**table_discovery_policy_output_fields(policy))
