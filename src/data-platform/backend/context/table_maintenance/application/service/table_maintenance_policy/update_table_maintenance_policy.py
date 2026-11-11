"""Define the UpdateTableMaintenancePolicyService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    MaintenancePolicyContent,
    TableMaintenancePolicyName,
)
from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table_maintenance_policy import (
    UpdateTableMaintenancePolicyUseCase,
    UpdateTableMaintenancePolicyUseCaseInput,
    UpdateTableMaintenancePolicyUseCaseOutput,
)
from context.table_maintenance.application.service.shared import (
    translate_domain_errors,
)
from context.table_maintenance.application.service.table_maintenance_policy.table_maintenance_policy_output_fields import (  # noqa: E501
    table_maintenance_policy_output_fields,
)
from context.table_maintenance.application.service.table_maintenance_policy_attachment import notify_policy_change

if TYPE_CHECKING:
    from collections.abc import Callable

    from context.table_maintenance.application.domain.model.table_maintenance_policy import (
        TableMaintenancePolicy,
    )
    from context.table_maintenance.application.port.outbound.table import SendTableChangeGateway, TablesRepo
    from context.table_maintenance.application.port.outbound.table_maintenance_policy import (
        TableMaintenancePoliciesRepo,
    )
    from context.table_maintenance.application.port.outbound.table_maintenance_policy_attachment import (
        TableMaintenancePolicyAttachmentsRepo,
    )


class UpdateTableMaintenancePolicyService(UpdateTableMaintenancePolicyUseCase):
    """Replace a table maintenance policy's content as a new version."""

    def __init__(
        self,
        policies_repo: TableMaintenancePoliciesRepo,
        attachments_repo: TableMaintenancePolicyAttachmentsRepo,
        tables_repo: TablesRepo,
        table_changes: SendTableChangeGateway,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Bind the repos, the table change gateway and the clock."""
        self._policies_repo = policies_repo
        self._attachments_repo = attachments_repo
        self._tables_repo = tables_repo
        self._table_changes = table_changes
        self._clock = clock

    def execute(self, request: UpdateTableMaintenancePolicyUseCaseInput) -> UpdateTableMaintenancePolicyUseCaseOutput:
        """Replace the content when ``version`` is the current one, else raise ConflictError.

        Every managed table the policy applies to is told that its policy changed.
        """
        with translate_domain_errors():
            name = TableMaintenancePolicyName(request.name)
            content = MaintenancePolicyContent.from_primitives(request.content)
        policy = self._policies_repo.get(name)
        if policy is None:
            raise NotFoundError(f"table maintenance policy {request.name} not found")
        notify_policy_change(
            self._tables_repo,
            self._policies_repo,
            self._attachments_repo,
            self._table_changes,
            lambda: self._replace(policy, content, request.version),
        )
        return UpdateTableMaintenancePolicyUseCaseOutput(**table_maintenance_policy_output_fields(policy))

    def _replace(self, policy: TableMaintenancePolicy, content: MaintenancePolicyContent, version: int) -> None:
        with translate_domain_errors():
            policy.replace(content, version, self._clock())
            self._policies_repo.update(policy)
