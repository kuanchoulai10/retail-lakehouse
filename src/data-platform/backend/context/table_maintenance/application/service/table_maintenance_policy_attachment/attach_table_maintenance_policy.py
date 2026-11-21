"""Define the AttachTableMaintenancePolicyService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table_maintenance_policy_attachment import (
    AttachTableMaintenancePolicyUseCase,
    AttachTableMaintenancePolicyUseCaseInput,
    AttachTableMaintenancePolicyUseCaseOutput,
)
from context.table_maintenance.application.port.outbound.table_maintenance_policy import (
    TableMaintenancePolicyName,
)
from context.table_maintenance.application.port.outbound.table_maintenance_policy_attachment import (
    TableMaintenancePolicyAttachment,
)
from context.table_maintenance.application.service.shared import policy_target_from_request, translate_domain_errors
from context.table_maintenance.application.service.table_maintenance_policy_attachment.notify_policy_change import (  # noqa: E501
    notify_policy_change,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from context.table_maintenance.application.port.outbound.table import (
        ReadTableMetadataGateway,
        SendTableChangeGateway,
        TablesRepo,
    )
    from context.table_maintenance.application.port.outbound.table_maintenance_policy import (
        TableMaintenancePoliciesRepo,
        TableMaintenancePolicyId,
    )
    from context.table_maintenance.application.port.outbound.table_maintenance_policy_attachment import (
        PolicyTarget,
        TableMaintenancePolicyAttachmentsRepo,
    )


class AttachTableMaintenancePolicyService(AttachTableMaintenancePolicyUseCase):
    """Attach a policy to a catalog, namespace or table, replacing the one already attached there."""

    def __init__(
        self,
        policies_repo: TableMaintenancePoliciesRepo,
        attachments_repo: TableMaintenancePolicyAttachmentsRepo,
        gateway: ReadTableMetadataGateway,
        tables_repo: TablesRepo,
        table_changes: SendTableChangeGateway,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Bind the repos, the catalog gateway, the table change gateway and the clock."""
        self._policies_repo = policies_repo
        self._attachments_repo = attachments_repo
        self._gateway = gateway
        self._tables_repo = tables_repo
        self._table_changes = table_changes
        self._clock = clock

    def execute(self, request: AttachTableMaintenancePolicyUseCaseInput) -> AttachTableMaintenancePolicyUseCaseOutput:
        """Attach the policy, rejecting a target missing from the catalog and an unknown policy.

        A target that already holds an attachment keeps its id. Every managed table whose applicable
        policy changes is told so.
        """
        with translate_domain_errors():
            policy_name = TableMaintenancePolicyName(value=request.policy_name)
        target = policy_target_from_request(self._gateway, request.target_type, request.path, must_exist=True)
        policy = self._policies_repo.get_by_name(policy_name)
        if policy is None:
            raise NotFoundError(f"table maintenance policy {request.policy_name} not found")
        policy_id = policy.id
        attachment = notify_policy_change(
            self._tables_repo,
            self._policies_repo,
            self._attachments_repo,
            self._table_changes,
            lambda: self._save(target, policy_id),
        )
        return AttachTableMaintenancePolicyUseCaseOutput(
            id=attachment.id.value,
            target_type=attachment.target.type.value,
            path=attachment.target.path,
            table_uuid=attachment.target.table_uuid,
            policy_id=attachment.policy_id.value,
            policy_name=policy.name.value,
            attached_at=attachment.attached_at,
        )

    def _save(self, target: PolicyTarget, policy_id: TableMaintenancePolicyId) -> TableMaintenancePolicyAttachment:
        now = self._clock()
        attachment = self._attachments_repo.get_by_target(target)
        if attachment is None:
            return self._attachments_repo.create(TableMaintenancePolicyAttachment.attach(target, policy_id, now))
        attachment.replace_policy(policy_id, now)
        return self._attachments_repo.update(attachment)
