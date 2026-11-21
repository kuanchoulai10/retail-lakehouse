"""Define the DetachTableDiscoveryPolicyService."""

from __future__ import annotations

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

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table_discovery_policy import (
        TableDiscoveryPoliciesRepo,
    )
    from context.table_maintenance.application.port.outbound.table_discovery_policy_attachment import (
        TableDiscoveryPolicyAttachmentsRepo,
    )


class DetachTableDiscoveryPolicyService(DetachTableDiscoveryPolicyUseCase):
    """Remove one of a discovery policy's attachments, named by its ``da-`` id."""

    def __init__(
        self,
        policies_repo: TableDiscoveryPoliciesRepo,
        attachments_repo: TableDiscoveryPolicyAttachmentsRepo,
    ) -> None:
        """Bind the repos."""
        self._policies_repo = policies_repo
        self._attachments_repo = attachments_repo

    def execute(self, request: DetachTableDiscoveryPolicyUseCaseInput) -> DetachTableDiscoveryPolicyUseCaseOutput:
        """Delete the attachment; a malformed id is ValidationError, and an unknown policy is NotFoundError.

        An id that is not stored, or that belongs to another policy, is NotFoundError. The catalog is not
        read, so an attachment whose target is gone is detached the same way.
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
        self._attachments_repo.delete(attachment_id)
        return DetachTableDiscoveryPolicyUseCaseOutput()
