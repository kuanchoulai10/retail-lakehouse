"""Define the ListTableMaintenancePolicyAttachmentsService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table_maintenance_policy_attachment import (
    ListTableMaintenancePolicyAttachmentsUseCase,
    ListTableMaintenancePolicyAttachmentsUseCaseInput,
    ListTableMaintenancePolicyAttachmentsUseCaseOutput,
)
from context.table_maintenance.application.port.outbound.table_maintenance_policy import (
    TableMaintenancePolicyName,
)
from context.table_maintenance.application.service.shared import target_in_catalog, translate_domain_errors

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table import ReadTableMetadataGateway, TablesRepo
    from context.table_maintenance.application.port.outbound.table_maintenance_policy import (
        TableMaintenancePoliciesRepo,
    )
    from context.table_maintenance.application.port.outbound.table_maintenance_policy_attachment import (
        TableMaintenancePolicyAttachmentsRepo,
    )


class ListTableMaintenancePolicyAttachmentsService(ListTableMaintenancePolicyAttachmentsUseCase):
    """List policy attachments, optionally only those of one policy, marking those left behind."""

    def __init__(
        self,
        policies_repo: TableMaintenancePoliciesRepo,
        attachments_repo: TableMaintenancePolicyAttachmentsRepo,
        gateway: ReadTableMetadataGateway,
        tables_repo: TablesRepo,
    ) -> None:
        """Bind the repos and the catalog gateway."""
        self._policies_repo = policies_repo
        self._attachments_repo = attachments_repo
        self._gateway = gateway
        self._tables_repo = tables_repo

    def execute(
        self, request: ListTableMaintenancePolicyAttachmentsUseCaseInput
    ) -> ListTableMaintenancePolicyAttachmentsUseCaseOutput:
        """Return the attachments, each orphaned when its target no longer exists; an unknown policy is not found.

        The attachments and their policies are two reads: an attachment whose policy was detached
        and deleted in between has no policy left to name, so it is skipped.
        """
        if request.policy_name is None:
            attachments = self._attachments_repo.list_all()
        else:
            with translate_domain_errors():
                name = TableMaintenancePolicyName(value=request.policy_name)
            policy = self._policies_repo.get_by_name(name)
            if policy is None:
                raise NotFoundError(f"table maintenance policy {request.policy_name} not found")
            attachments = self._attachments_repo.list_for_policy(policy.id)
        names = {p.id.value: p.name.value for p in self._policies_repo.get_many([a.policy_id for a in attachments])}
        return ListTableMaintenancePolicyAttachmentsUseCaseOutput(
            items=tuple(
                ListTableMaintenancePolicyAttachmentsUseCaseOutput.TableMaintenancePolicyAttachment(
                    type=a.target.type.value,
                    path=a.target.path,
                    table_uuid=a.target.table_uuid,
                    policy_id=a.policy_id.value,
                    policy_name=names[a.policy_id.value],
                    attached_at=a.attached_at,
                    orphaned=not target_in_catalog(a.target, self._gateway, self._tables_repo),
                )
                for a in attachments
                if a.policy_id.value in names
            )
        )
