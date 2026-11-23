"""Define the GetTableReconciliationService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import TableReconciliationId
from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table_reconciliation import (
    GetTableReconciliationUseCase,
    GetTableReconciliationUseCaseInput,
    GetTableReconciliationUseCaseOutput,
)
from context.table_maintenance.application.service.table_reconciliation.table_reconciliation_output_fields import (
    table_reconciliation_output_fields,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table_maintenance_policy import (
        TableMaintenancePoliciesRepo,
    )
    from context.table_maintenance.application.port.outbound.table_reconciliation import (
        TableReconciliationsRepo,
    )


class GetTableReconciliationService(GetTableReconciliationUseCase):
    """Get one reconciliation, naming its policy as the listing does."""

    def __init__(
        self, reconciliations_repo: TableReconciliationsRepo, policies_repo: TableMaintenancePoliciesRepo
    ) -> None:
        """Bind the reconciliations repo and the policies repo the current policy name is read from."""
        self._reconciliations_repo = reconciliations_repo
        self._policies_repo = policies_repo

    def execute(self, request: GetTableReconciliationUseCaseInput) -> GetTableReconciliationUseCaseOutput:
        """Return the reconciliation or raise NotFoundError; a malformed id is refused as invalid."""
        reconciliation = self._reconciliations_repo.get(TableReconciliationId(request.reconciliation_id))
        if reconciliation is None:
            raise NotFoundError(f"table reconciliation {request.reconciliation_id} not found")
        names = {
            policy.id.value: policy.name.value for policy in self._policies_repo.get_many([reconciliation.policy_id])
        }
        return GetTableReconciliationUseCaseOutput(**table_reconciliation_output_fields(reconciliation, names))
