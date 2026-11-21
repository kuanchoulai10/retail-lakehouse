"""Define the DetachTableDiscoveryPolicyService."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table_discovery_policy_attachment import (
    DetachTableDiscoveryPolicyUseCase,
    DetachTableDiscoveryPolicyUseCaseInput,
    DetachTableDiscoveryPolicyUseCaseOutput,
)
from context.table_maintenance.application.port.outbound.table_discovery_policy import (
    TableDiscoveryPolicyName,
)
from context.table_maintenance.application.port.outbound.table_discovery_policy_attachment import (
    TableDiscoveryPolicyAttachmentId,
)
from context.table_maintenance.application.service.shared import translate_domain_errors
from context.table_maintenance.application.service.table_discovery_policy_attachment.apply_discovery_change import (
    apply_discovery_change,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from context.table_maintenance.application.port.outbound.table import SendDiscoveryRequestGateway
    from context.table_maintenance.application.port.outbound.table_discovery_policy import (
        TableDiscoveryPoliciesRepo,
    )
    from context.table_maintenance.application.port.outbound.table_discovery_policy_attachment import (
        SyncDiscoverySchedulesGateway,
        TableDiscoveryPolicyAttachmentsRepo,
    )


class DetachTableDiscoveryPolicyService(DetachTableDiscoveryPolicyUseCase):
    """Remove one of a discovery policy's attachments, named by its ``da-`` id."""

    def __init__(
        self,
        policies_repo: TableDiscoveryPoliciesRepo,
        attachments_repo: TableDiscoveryPolicyAttachmentsRepo,
        discovery_requests: SendDiscoveryRequestGateway,
        schedules: SyncDiscoverySchedulesGateway,
        *,
        new_change_id: Callable[[], str] = lambda: uuid.uuid4().hex,
    ) -> None:
        """Bind the repos, the discovery requests, the schedules and the change id generator."""
        self._policies_repo = policies_repo
        self._attachments_repo = attachments_repo
        self._discovery_requests = discovery_requests
        self._schedules = schedules
        self._new_change_id = new_change_id

    def execute(self, request: DetachTableDiscoveryPolicyUseCaseInput) -> DetachTableDiscoveryPolicyUseCaseOutput:
        """Delete the attachment; a malformed id is ValidationError, and an unknown policy is NotFoundError.

        An id that is not stored, or that belongs to another policy, is NotFoundError. The catalog is not
        read, so an attachment whose target is gone is detached the same way. Once deleted, the target's
        catalog is rescanned and the discovery schedules are synced, best effort (see
        ``apply_discovery_change``); a refused detach does neither.
        """
        with translate_domain_errors():
            policy_name = TableDiscoveryPolicyName(value=request.policy_name)
            attachment_id = TableDiscoveryPolicyAttachmentId(request.attachment_id)
        policy = self._policies_repo.get_by_name(policy_name)
        if policy is None:
            raise NotFoundError(f"discovery policy {request.policy_name} not found")
        attachment = self._attachments_repo.get(attachment_id)
        if attachment is None or attachment.policy_id != policy.id:
            raise NotFoundError(f"policy {policy.name.value} has no attachment {attachment_id.value}")
        apply_discovery_change(
            self._policies_repo,
            self._attachments_repo,
            self._discovery_requests,
            self._schedules,
            lambda: self._attachments_repo.delete(attachment_id),
            affected_catalogs=lambda: {attachment.target.path[0]},
            change_id=self._new_change_id(),
        )
        return DetachTableDiscoveryPolicyUseCaseOutput()
