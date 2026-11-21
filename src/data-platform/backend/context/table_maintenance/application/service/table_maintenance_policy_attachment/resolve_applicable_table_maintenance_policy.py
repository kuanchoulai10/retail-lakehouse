"""Define the ResolveApplicableTableMaintenancePolicyService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    DEFAULT_POLICY_ID,
)
from context.table_maintenance.application.domain.service.shared import nearest_attached
from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table_maintenance_policy_attachment import (
    ResolveApplicableTableMaintenancePolicyUseCase,
    ResolveApplicableTableMaintenancePolicyUseCaseInput,
    ResolveApplicableTableMaintenancePolicyUseCaseOutput,
)
from context.table_maintenance.application.service.shared import policy_candidates, policy_target_fields

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table import ReadTableMetadataGateway, TablesRepo
    from context.table_maintenance.application.port.outbound.table_maintenance_policy import (
        TableMaintenancePoliciesRepo,
    )
    from context.table_maintenance.application.port.outbound.table_maintenance_policy_attachment import (
        TableMaintenancePolicyAttachmentsRepo,
    )


class ResolveApplicableTableMaintenancePolicyService(ResolveApplicableTableMaintenancePolicyUseCase):
    """Find the policy that applies to a table, namespace or catalog: the nearest attachment wins."""

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
        self, request: ResolveApplicableTableMaintenancePolicyUseCaseInput
    ) -> ResolveApplicableTableMaintenancePolicyUseCaseOutput:
        """Return the nearest attached policy, or the default one with no target."""
        candidates = policy_candidates(
            self._gateway,
            self._tables_repo,
            catalog=request.catalog,
            namespace=request.namespace,
            table=request.table,
            table_uuid=request.table_uuid,
        )
        attached = {a.target.key(): a.policy_id for a in self._attachments_repo.get_many_by_targets(candidates)}
        nearest = nearest_attached(candidates, attached)
        matched, policy_id = (None, DEFAULT_POLICY_ID) if nearest is None else nearest
        policy = self._policies_repo.get(policy_id)
        if policy is None:
            raise NotFoundError(f"table maintenance policy {policy_id.value} not found")
        return ResolveApplicableTableMaintenancePolicyUseCaseOutput(
            policy_id=policy.id.value,
            policy_name=policy.name.value,
            version=policy.version,
            content=policy.content.to_primitives(),
            target=None if matched is None else policy_target_fields(matched),
        )
