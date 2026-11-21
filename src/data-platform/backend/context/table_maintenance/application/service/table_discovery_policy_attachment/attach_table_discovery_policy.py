"""Define the AttachTableDiscoveryPolicyService."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table_discovery_policy_attachment import (
    AttachTableDiscoveryPolicyUseCase,
    AttachTableDiscoveryPolicyUseCaseInput,
    AttachTableDiscoveryPolicyUseCaseOutput,
)
from context.table_maintenance.application.port.outbound.table_discovery_policy import (
    TableDiscoveryPolicyName,
)
from context.table_maintenance.application.port.outbound.table_discovery_policy_attachment import (
    TableDiscoveryPolicyAttachment,
)
from context.table_maintenance.application.service.shared import policy_target_from_request, translate_domain_errors
from context.table_maintenance.application.service.table_discovery_policy_attachment.apply_discovery_change import (
    apply_discovery_change,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from context.table_maintenance.application.port.outbound.table import (
        ReadTableMetadataGateway,
        SendDiscoveryRequestGateway,
    )
    from context.table_maintenance.application.port.outbound.table_discovery_policy import (
        TableDiscoveryPoliciesRepo,
        TableDiscoveryPolicyId,
    )
    from context.table_maintenance.application.port.outbound.table_discovery_policy_attachment import (
        PolicyTarget,
        SyncDiscoverySchedulesGateway,
        TableDiscoveryPolicyAttachmentsRepo,
    )


class AttachTableDiscoveryPolicyService(AttachTableDiscoveryPolicyUseCase):
    """Attach a discovery policy to a catalog, namespace or table, replacing the one already attached there."""

    def __init__(  # noqa: PLR0913
        self,
        policies_repo: TableDiscoveryPoliciesRepo,
        attachments_repo: TableDiscoveryPolicyAttachmentsRepo,
        gateway: ReadTableMetadataGateway,
        discovery_requests: SendDiscoveryRequestGateway,
        schedules: SyncDiscoverySchedulesGateway,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        new_change_id: Callable[[], str] = lambda: uuid.uuid4().hex,
    ) -> None:
        """Bind the repos, the catalog gateway, the discovery requests, the schedules, the clock and the change ids."""
        self._policies_repo = policies_repo
        self._attachments_repo = attachments_repo
        self._gateway = gateway
        self._discovery_requests = discovery_requests
        self._schedules = schedules
        self._clock = clock
        self._new_change_id = new_change_id

    def execute(self, request: AttachTableDiscoveryPolicyUseCaseInput) -> AttachTableDiscoveryPolicyUseCaseOutput:
        """Attach the policy; a target or policy that does not exist is NotFoundError.

        The target must exist in the catalog, though a catalog or namespace may be empty, and a table is
        keyed by the uuid the catalog gives it. A target in a catalog the platform's credential cannot
        read raises CatalogAccessDeniedError. A target that already holds an attachment keeps its id.
        Once stored, the target's catalog is rescanned and the discovery schedules are synced, best
        effort (see ``apply_discovery_change``); a refused attach does neither.
        """
        with translate_domain_errors():
            policy_name = TableDiscoveryPolicyName(value=request.policy_name)
        target = policy_target_from_request(self._gateway, request.target_type, request.path)
        policy = self._policies_repo.get_by_name(policy_name)
        if policy is None:
            raise NotFoundError(f"discovery policy {request.policy_name} not found")
        attachment = apply_discovery_change(
            self._policies_repo,
            self._attachments_repo,
            self._discovery_requests,
            self._schedules,
            lambda: self._save(target, policy.id),
            affected_catalogs=lambda: {target.path[0]},
            change_id=self._new_change_id(),
        )
        return AttachTableDiscoveryPolicyUseCaseOutput(
            id=attachment.id.value,
            target_type=attachment.target.type.value,
            path=attachment.target.path,
            table_uuid=attachment.target.table_uuid,
            policy_id=attachment.policy_id.value,
            policy_name=policy.name.value,
            attached_at=attachment.attached_at,
        )

    def _save(self, target: PolicyTarget, policy_id: TableDiscoveryPolicyId) -> TableDiscoveryPolicyAttachment:
        now = self._clock()
        attachment = self._attachments_repo.get_by_target(target)
        if attachment is None:
            return self._attachments_repo.create(TableDiscoveryPolicyAttachment.attach(target, policy_id, now))
        attachment.replace_policy(policy_id, now)
        return self._attachments_repo.update(attachment)
