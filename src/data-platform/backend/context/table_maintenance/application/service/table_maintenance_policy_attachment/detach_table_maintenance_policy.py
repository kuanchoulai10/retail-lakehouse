"""Define the DetachTableMaintenancePolicyService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table_maintenance_policy_attachment import (
    DetachTableMaintenancePolicyUseCase,
    DetachTableMaintenancePolicyUseCaseInput,
    DetachTableMaintenancePolicyUseCaseOutput,
)
from context.table_maintenance.application.port.outbound.table_maintenance_policy import (
    TableMaintenancePolicyName,
)
from context.table_maintenance.application.port.outbound.table_maintenance_policy_attachment import (
    TableMaintenancePolicyAttachmentId,
)
from context.table_maintenance.application.service.shared import translate_domain_errors
from context.table_maintenance.application.service.table_maintenance_policy_attachment.notify_policy_change import (  # noqa: E501
    notify_policy_change,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table import SendTableChangeGateway, TablesRepo
    from context.table_maintenance.application.port.outbound.table_maintenance_policy import (
        TableMaintenancePoliciesRepo,
    )
    from context.table_maintenance.application.port.outbound.table_maintenance_policy_attachment import (
        TableMaintenancePolicyAttachmentsRepo,
    )


class DetachTableMaintenancePolicyService(DetachTableMaintenancePolicyUseCase):
    """Remove one of a maintenance policy's attachments, named by its ``pa-`` id."""

    def __init__(
        self,
        policies_repo: TableMaintenancePoliciesRepo,
        attachments_repo: TableMaintenancePolicyAttachmentsRepo,
        tables_repo: TablesRepo,
        table_changes: SendTableChangeGateway,
    ) -> None:
        """Bind the repos and the table change gateway."""
        self._policies_repo = policies_repo
        self._attachments_repo = attachments_repo
        self._tables_repo = tables_repo
        self._table_changes = table_changes

    def execute(self, request: DetachTableMaintenancePolicyUseCaseInput) -> DetachTableMaintenancePolicyUseCaseOutput:
        """Delete the attachment; a malformed id is ValidationError, and an unknown policy is NotFoundError.

        An id that is not stored, or that belongs to another policy, is NotFoundError. The catalog is not
        read, so an attachment whose target is gone is detached the same way. Every managed table whose
        applicable policy changes is told so; a refused detach tells none.
        """
        with translate_domain_errors():
            policy_name = TableMaintenancePolicyName(value=request.policy_name)
            attachment_id = TableMaintenancePolicyAttachmentId(request.attachment_id)
        policy = self._policies_repo.get_by_name(policy_name)
        if policy is None:
            raise NotFoundError(f"table maintenance policy {request.policy_name} not found")
        attachment = self._attachments_repo.get(attachment_id)
        if attachment is None or attachment.policy_id != policy.id:
            raise NotFoundError(f"policy {policy.name.value} has no attachment {attachment_id.value}")
        notify_policy_change(
            self._tables_repo,
            self._policies_repo,
            self._attachments_repo,
            self._table_changes,
            lambda: self._attachments_repo.delete(attachment_id),
        )
        return DetachTableMaintenancePolicyUseCaseOutput()
