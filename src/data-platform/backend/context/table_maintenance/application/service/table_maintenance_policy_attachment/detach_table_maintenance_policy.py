"""Define the DetachTableMaintenancePolicyService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table_maintenance_policy_attachment import (
    DetachTableMaintenancePolicyUseCase,
    DetachTableMaintenancePolicyUseCaseInput,
    DetachTableMaintenancePolicyUseCaseOutput,
)
from context.table_maintenance.application.service.table_maintenance_policy_attachment.policy_target_from_request import (  # noqa: E501
    policy_target_from_request,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table import ReadTableMetadataGateway
    from context.table_maintenance.application.port.outbound.table_maintenance_policy_attachment import (
        TableMaintenancePolicyAttachmentsRepo,
    )


class DetachTableMaintenancePolicyService(DetachTableMaintenancePolicyUseCase):
    """Remove the policy attached to a catalog, namespace or table."""

    def __init__(
        self, attachments_repo: TableMaintenancePolicyAttachmentsRepo, gateway: ReadTableMetadataGateway
    ) -> None:
        """Bind the repo and the catalog gateway."""
        self._attachments_repo = attachments_repo
        self._gateway = gateway

    def execute(self, request: DetachTableMaintenancePolicyUseCaseInput) -> DetachTableMaintenancePolicyUseCaseOutput:
        """Detach the policy; a target with nothing attached is NotFoundError."""
        target = policy_target_from_request(
            self._gateway, request.target_type, request.path, request.table_uuid, must_exist=False
        )
        if self._attachments_repo.get(target.attachment_id()) is None:
            raise NotFoundError(f"no policy is attached to {request.target_type} {'.'.join(request.path)}")
        self._attachments_repo.delete(target.attachment_id())
        return DetachTableMaintenancePolicyUseCaseOutput()
