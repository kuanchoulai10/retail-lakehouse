"""Define the ResolveApplicableTableMaintenancePolicyService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table import TableId, TableName
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    DEFAULT_POLICY_ID,
)
from context.table_maintenance.application.domain.service.shared import (
    candidate_policy_targets,
    enclosing_policy_targets,
    nearest_attached,
)
from context.table_maintenance.application.exceptions import NotFoundError, ValidationError
from context.table_maintenance.application.port.inbound.table_maintenance_policy_attachment import (
    ResolveApplicableTableMaintenancePolicyUseCase,
    ResolveApplicableTableMaintenancePolicyUseCaseInput,
    ResolveApplicableTableMaintenancePolicyUseCaseOutput,
)
from context.table_maintenance.application.port.outbound.table import CatalogNotFoundError, TableMetadataRef
from context.table_maintenance.application.service.shared import translate_domain_errors

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.shared import PolicyTarget
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
        candidates = self._candidates(request)
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
            target=None if matched is None else _target_fields(matched),
        )

    def _candidates(self, request: ResolveApplicableTableMaintenancePolicyUseCaseInput) -> tuple[PolicyTarget, ...]:
        if request.catalog is None:
            return self._registered_table_candidates(request.table_uuid)
        if request.table is None:
            return enclosing_policy_targets(request.catalog, request.namespace)
        if request.namespace is None:
            raise ValidationError("a table needs its namespace")
        table_uuid = request.table_uuid
        if table_uuid is None:
            try:
                loaded = self._gateway.load_table(
                    TableMetadataRef(catalog=request.catalog, namespace=request.namespace, table=request.table)
                )
            except CatalogNotFoundError as exc:
                raise NotFoundError(str(exc)) from exc
            if loaded is None:
                raise NotFoundError(f"table {request.catalog}.{request.namespace}.{request.table} not found")
            table_uuid = loaded.table_uuid
        with translate_domain_errors():
            name = TableName(catalog=request.catalog, namespace=request.namespace, table=request.table)
            return candidate_policy_targets(name, table_uuid)

    def _registered_table_candidates(self, table_uuid: str | None) -> tuple[PolicyTarget, ...]:
        if table_uuid is None:
            raise ValidationError("name a catalog or a table uuid")
        table = self._tables_repo.get(TableId(table_uuid))
        if table is None:
            raise NotFoundError(f"table {table_uuid} not found")
        return candidate_policy_targets(table.name, table.id.value)


def _target_fields(target: PolicyTarget) -> dict[str, object]:
    fields: dict[str, object] = {"type": target.type.value, "path": list(target.path)}
    if target.table_uuid is not None:
        fields["table_uuid"] = target.table_uuid
    return fields
