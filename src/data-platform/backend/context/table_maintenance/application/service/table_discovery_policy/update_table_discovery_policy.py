"""Define the UpdateTableDiscoveryPolicyService."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

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
from context.table_maintenance.application.service.table_discovery_policy.table_discovery_policy_output_fields import (  # noqa: E501
    table_discovery_policy_output_fields,
)
from context.table_maintenance.application.service.table_discovery_policy_attachment import (
    apply_discovery_change,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from context.table_maintenance.application.port.outbound.table import SendDiscoveryRequestGateway
    from context.table_maintenance.application.port.outbound.table_discovery_policy import (
        TableDiscoveryPoliciesRepo,
        TableDiscoveryPolicy,
    )
    from context.table_maintenance.application.port.outbound.table_discovery_policy_attachment import (
        SyncDiscoverySchedulesGateway,
        TableDiscoveryPolicyAttachmentsRepo,
    )


class UpdateTableDiscoveryPolicyService(UpdateTableDiscoveryPolicyUseCase):
    """Revise a discovery policy's description and rules as a new version."""

    def __init__(  # noqa: PLR0913
        self,
        policies_repo: TableDiscoveryPoliciesRepo,
        attachments_repo: TableDiscoveryPolicyAttachmentsRepo,
        discovery_requests: SendDiscoveryRequestGateway,
        schedules: SyncDiscoverySchedulesGateway,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        new_change_id: Callable[[], str] = lambda: uuid.uuid4().hex,
    ) -> None:
        """Bind the repos, the discovery requests, the schedules, the clock and the change id generator."""
        self._policies_repo = policies_repo
        self._attachments_repo = attachments_repo
        self._discovery_requests = discovery_requests
        self._schedules = schedules
        self._clock = clock
        self._new_change_id = new_change_id

    def execute(self, request: UpdateTableDiscoveryPolicyUseCaseInput) -> UpdateTableDiscoveryPolicyUseCaseOutput:
        """Replace the description and the rules when ``version`` is the current one.

        Bad rules (none, an unknown action, an empty pattern, a missing or unknown field) raise
        ValidationError; a stale version (also one a concurrent writer made stale) raises ConflictError.
        Either way nothing is saved, synced or scanned. Once saved, every catalog the policy is attached
        in is rescanned and the discovery schedules are synced, best effort (see ``apply_discovery_change``).
        """
        with translate_domain_errors():
            name = TableDiscoveryPolicyName(value=request.name)
            rules = discovery_rules_of(request.rules)
        policy = self._policies_repo.get_by_name(name)
        if policy is None:
            raise NotFoundError(f"discovery policy {request.name} not found")

        def revise() -> None:
            with translate_domain_errors():
                policy.revise(request.description, rules, request.version, self._clock())
                self._policies_repo.update(policy)

        apply_discovery_change(
            self._policies_repo,
            self._attachments_repo,
            self._discovery_requests,
            self._schedules,
            revise,
            affected_catalogs=lambda: self._attached_catalogs(policy),
            change_id=self._new_change_id(),
        )
        return UpdateTableDiscoveryPolicyUseCaseOutput(**table_discovery_policy_output_fields(policy))

    def _attached_catalogs(self, policy: TableDiscoveryPolicy) -> set[str]:
        return {a.catalog for a in self._attachments_repo.list_for_policy(policy.id)}
