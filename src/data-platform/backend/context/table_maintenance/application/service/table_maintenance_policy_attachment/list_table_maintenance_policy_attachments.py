"""Define the ListTableMaintenancePolicyAttachmentsService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.port.inbound.table_maintenance_policy_attachment import (
    ListTableMaintenancePolicyAttachmentsUseCase,
    ListTableMaintenancePolicyAttachmentsUseCaseInput,
    ListTableMaintenancePolicyAttachmentsUseCaseOutput,
    ListTableMaintenancePolicyAttachmentsUseCaseOutputItem,
)
from context.table_maintenance.application.port.outbound.table_maintenance_policy_attachment import (
    TableMaintenancePolicyName,
)
from context.table_maintenance.application.service.shared import translate_domain_errors

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table_maintenance_policy_attachment import (
        TableMaintenancePolicyAttachmentsRepo,
    )


class ListTableMaintenancePolicyAttachmentsService(ListTableMaintenancePolicyAttachmentsUseCase):
    """List policy attachments, optionally only those of one policy."""

    def __init__(self, attachments_repo: TableMaintenancePolicyAttachmentsRepo) -> None:
        """Bind the repo."""
        self._attachments_repo = attachments_repo

    def execute(
        self, request: ListTableMaintenancePolicyAttachmentsUseCaseInput
    ) -> ListTableMaintenancePolicyAttachmentsUseCaseOutput:
        """Return the attachments."""
        if request.policy_name is None:
            attachments = self._attachments_repo.list_all()
        else:
            with translate_domain_errors():
                name = TableMaintenancePolicyName(request.policy_name)
            attachments = self._attachments_repo.list_for_policy(name)
        return ListTableMaintenancePolicyAttachmentsUseCaseOutput(
            items=[
                ListTableMaintenancePolicyAttachmentsUseCaseOutputItem(
                    type=a.target.type.value,
                    path=a.target.path,
                    table_uuid=a.target.table_uuid,
                    policy_name=a.policy_name.value,
                    attached_at=a.attached_at,
                )
                for a in attachments
            ]
        )
