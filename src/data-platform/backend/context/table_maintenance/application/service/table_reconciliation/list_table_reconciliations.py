"""Define the ListTableReconciliationsService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table import TableId
from context.table_maintenance.application.port.inbound.table_reconciliation import (
    ListTableReconciliationsUseCase,
    ListTableReconciliationsUseCaseInput,
    ListTableReconciliationsUseCaseOutput,
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


class ListTableReconciliationsService(ListTableReconciliationsUseCase):
    """List the reconciliations of a table, newest first."""

    def __init__(
        self, reconciliations_repo: TableReconciliationsRepo, policies_repo: TableMaintenancePoliciesRepo
    ) -> None:
        """Bind the reconciliations repo and the policies repo the current policy names are read from."""
        self._reconciliations_repo = reconciliations_repo
        self._policies_repo = policies_repo

    def execute(self, request: ListTableReconciliationsUseCaseInput) -> ListTableReconciliationsUseCaseOutput:
        """Return up to ``limit`` reconciliations strictly before ``before``, each naming its policy by id and name.

        A policy that still exists is named as it is now; one deleted since keeps the name the
        record took when it was written, and is flagged as deleted.
        """
        found = self._reconciliations_repo.list_by_table(
            TableId(request.table_uuid), before=request.before, limit=request.limit
        )
        names = {
            policy.id.value: policy.name.value
            for policy in self._policies_repo.get_many(list({r.policy_id: None for r in found}))
        }
        return ListTableReconciliationsUseCaseOutput(
            items=tuple(
                ListTableReconciliationsUseCaseOutput.TableReconciliation(
                    **table_reconciliation_output_fields(r, names)
                )
                for r in found
            )
        )
