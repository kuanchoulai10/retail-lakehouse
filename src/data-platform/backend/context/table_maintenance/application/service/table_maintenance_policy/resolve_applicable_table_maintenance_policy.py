"""Define the ResolveApplicableTableMaintenancePolicyService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table_maintenance_policy import DEFAULT_POLICY_ID
from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table_maintenance_policy import (
    ResolveApplicableTableMaintenancePolicyUseCase,
    ResolveApplicableTableMaintenancePolicyUseCaseInput,
    ResolveApplicableTableMaintenancePolicyUseCaseOutput,
)
from context.table_maintenance.application.service.shared import PolicyHolders, policy_target_fields

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.catalog import CatalogsRepo
    from context.table_maintenance.application.port.outbound.namespace import NamespacesRepo
    from context.table_maintenance.application.port.outbound.table import ReadTableMetadataGateway, TablesRepo
    from context.table_maintenance.application.port.outbound.table_maintenance_policy import (
        TableMaintenancePoliciesRepo,
    )


class ResolveApplicableTableMaintenancePolicyService(ResolveApplicableTableMaintenancePolicyUseCase):
    """Find the maintenance policy that applies to a table, namespace or catalog: the nearest holder's wins."""

    def __init__(
        self,
        policies_repo: TableMaintenancePoliciesRepo,
        catalogs_repo: CatalogsRepo,
        namespaces_repo: NamespacesRepo,
        gateway: ReadTableMetadataGateway,
        tables_repo: TablesRepo,
    ) -> None:
        """Bind the policies, the place repos, the catalog gateway and the tables repo."""
        self._policies_repo = policies_repo
        self._catalogs_repo = catalogs_repo
        self._namespaces_repo = namespaces_repo
        self._gateway = gateway
        self._tables_repo = tables_repo

    def execute(
        self, request: ResolveApplicableTableMaintenancePolicyUseCaseInput
    ) -> ResolveApplicableTableMaintenancePolicyUseCaseOutput:
        """Return the nearest maintenance policy the table, its namespaces or its catalog hold, else the default.

        The place's holders are read as ``PolicyHolders.of_place`` reads them; the default answers with
        no target.
        """
        holders = PolicyHolders.of_place(
            self._gateway,
            self._tables_repo,
            self._catalogs_repo,
            self._namespaces_repo,
            catalog=request.catalog,
            namespace=request.namespace,
            table=request.table,
            table_uuid=request.table_uuid,
        )
        nearest = holders.nearest_maintenance_policy()
        policy_id = DEFAULT_POLICY_ID if nearest is None else nearest.policy_id
        policy = self._policies_repo.get(policy_id)
        if policy is None:
            raise NotFoundError(f"table maintenance policy {policy_id.value} not found")
        return ResolveApplicableTableMaintenancePolicyUseCaseOutput(
            policy_id=policy.id.value,
            policy_name=policy.name.value,
            version=policy.version,
            content=policy.content.to_primitives(),
            target=None if nearest is None else policy_target_fields(nearest.target),
        )
