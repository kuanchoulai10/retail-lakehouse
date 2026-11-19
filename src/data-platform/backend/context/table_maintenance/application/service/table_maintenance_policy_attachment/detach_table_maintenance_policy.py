"""Define the DetachTableMaintenancePolicyService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table_maintenance_policy_attachment import (
    DetachTableMaintenancePolicyUseCase,
    DetachTableMaintenancePolicyUseCaseInput,
    DetachTableMaintenancePolicyUseCaseOutput,
)
from context.table_maintenance.application.service.table_maintenance_policy_attachment.notify_policy_change import (  # noqa: E501
    notify_policy_change,
)
from context.table_maintenance.application.service.table_maintenance_policy_attachment.policy_target_from_request import (  # noqa: E501
    policy_target_from_request,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table import (
        ReadTableMetadataGateway,
        SendTableChangeGateway,
        TablesRepo,
    )
    from context.table_maintenance.application.port.outbound.table_maintenance_policy import (
        TableMaintenancePoliciesRepo,
    )
    from context.table_maintenance.application.port.outbound.table_maintenance_policy_attachment import (
        TableMaintenancePolicyAttachmentsRepo,
    )


class DetachTableMaintenancePolicyService(DetachTableMaintenancePolicyUseCase):
    """Remove the policy attached to a catalog, namespace or table."""

    def __init__(
        self,
        policies_repo: TableMaintenancePoliciesRepo,
        attachments_repo: TableMaintenancePolicyAttachmentsRepo,
        gateway: ReadTableMetadataGateway,
        tables_repo: TablesRepo,
        table_changes: SendTableChangeGateway,
    ) -> None:
        """Bind the repos, the catalog gateway and the table change gateway."""
        self._policies_repo = policies_repo
        self._attachments_repo = attachments_repo
        self._gateway = gateway
        self._tables_repo = tables_repo
        self._table_changes = table_changes

    def execute(self, request: DetachTableMaintenancePolicyUseCaseInput) -> DetachTableMaintenancePolicyUseCaseOutput:
        """Detach the policy and tell every managed table whose applicable policy changes.

        A target with nothing attached, or with another policy than ``policy_name`` when it is
        given, is NotFoundError.
        """
        target = policy_target_from_request(
            self._gateway, request.target_type, request.path, request.table_uuid, must_exist=False
        )
        attachment = self._attachments_repo.get_by_target(target)
        described = f"{request.target_type} {'.'.join(request.path)}"
        if attachment is None:
            raise NotFoundError(f"no policy is attached to {described}")
        if request.policy_name is not None and attachment.policy_name.value != request.policy_name:
            raise NotFoundError(f"policy {request.policy_name} is not attached to {described}")
        attachment_id = attachment.id
        notify_policy_change(
            self._tables_repo,
            self._policies_repo,
            self._attachments_repo,
            self._table_changes,
            lambda: self._attachments_repo.delete(attachment_id),
        )
        return DetachTableMaintenancePolicyUseCaseOutput()
