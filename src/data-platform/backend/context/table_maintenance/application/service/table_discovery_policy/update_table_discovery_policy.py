"""Define the UpdateTableDiscoveryPolicyService."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import TableDiscoveryRuleId
from context.table_maintenance.application.domain.model.table_discovery_policy import (
    DiscoveryPolicyContent,
    TableDiscoveryPolicyName,
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
    """Replace a discovery policy's content as a new version."""

    def __init__(  # noqa: PLR0913
        self,
        policies_repo: TableDiscoveryPoliciesRepo,
        attachments_repo: TableDiscoveryPolicyAttachmentsRepo,
        discovery_requests: SendDiscoveryRequestGateway,
        schedules: SyncDiscoverySchedulesGateway,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        new_id: Callable[[], str] = lambda: TableDiscoveryRuleId.new().value,
        new_change_id: Callable[[], str] = lambda: uuid.uuid4().hex,
    ) -> None:
        """Bind the repos, the discovery requests, the schedules, the clock and the id generators."""
        self._policies_repo = policies_repo
        self._attachments_repo = attachments_repo
        self._discovery_requests = discovery_requests
        self._schedules = schedules
        self._clock = clock
        self._new_id = new_id
        self._new_change_id = new_change_id

    def execute(self, request: UpdateTableDiscoveryPolicyUseCaseInput) -> UpdateTableDiscoveryPolicyUseCaseOutput:
        """Replace the content when ``version`` is the current one.

        A rule sent without an id gets a new ``dr-`` id; a rule sent with one keeps it, and the id must
        be one the current version holds. Invalid content, an empty or unknown rule id raises
        ValidationError; the default, or a stale version (also one a concurrent writer made stale), raises
        ConflictError. Either way nothing is saved, synced or scanned. Once saved, every catalog the
        policy is attached in is rescanned and the discovery schedules are synced, best effort (see
        ``apply_discovery_change``).
        """
        with translate_domain_errors():
            name = TableDiscoveryPolicyName(value=request.name)
            primitives, new_ids = content_with_issued_rule_ids(request.content, self._new_id)
            content = DiscoveryPolicyContent.from_primitives(primitives)
        policy = self._policies_repo.get_by_name(name)
        if policy is None:
            raise NotFoundError(f"discovery policy {request.name} not found")

        def replace() -> None:
            with translate_domain_errors():
                policy.replace(
                    content,
                    request.version,
                    self._clock(),
                    new_rule_ids={TableDiscoveryRuleId(i) for i in new_ids},
                )
                self._policies_repo.update(policy)

        apply_discovery_change(
            self._policies_repo,
            self._attachments_repo,
            self._discovery_requests,
            self._schedules,
            replace,
            affected_catalogs=lambda: self._attached_catalogs(policy),
            change_id=self._new_change_id(),
        )
        return UpdateTableDiscoveryPolicyUseCaseOutput(**table_discovery_policy_output_fields(policy))

    def _attached_catalogs(self, policy: TableDiscoveryPolicy) -> set[str]:
        return {a.catalog for a in self._attachments_repo.list_for_policy(policy.id)}
