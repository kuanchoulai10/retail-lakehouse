"""Define the ResolveApplicableTableMaintenancePolicyService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table import TableName
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    DEFAULT_POLICY_NAME,
    TableMaintenancePolicyName,
)
from context.table_maintenance.application.domain.service.table_maintenance_policy_attachment import (
    candidate_policy_targets,
    enclosing_policy_targets,
)
from context.table_maintenance.application.exceptions import NotFoundError, ValidationError
from context.table_maintenance.application.port.inbound.table_maintenance_policy_attachment import (
    ResolveApplicableTableMaintenancePolicyUseCase,
    ResolveApplicableTableMaintenancePolicyUseCaseInput,
    ResolveApplicableTableMaintenancePolicyUseCaseOutput,
)
from context.table_maintenance.application.port.outbound.table import TableMetadataRef
from context.table_maintenance.application.service.shared import translate_domain_errors

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.table_maintenance_policy_attachment import PolicyTarget
    from context.table_maintenance.application.port.outbound.table import ReadTableMetadataGateway
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
    ) -> None:
        """Bind the repos and the catalog gateway."""
        self._policies_repo = policies_repo
        self._attachments_repo = attachments_repo
        self._gateway = gateway

    def execute(
        self, request: ResolveApplicableTableMaintenancePolicyUseCaseInput
    ) -> ResolveApplicableTableMaintenancePolicyUseCaseOutput:
        """Return the nearest attached policy, or the default one with no target."""
        candidates = self._candidates(request)
        attached = {a.id: a for a in self._attachments_repo.get_many([c.attachment_id() for c in candidates])}
        matched = next((c for c in candidates if c.attachment_id() in attached), None)
        name = (
            TableMaintenancePolicyName(DEFAULT_POLICY_NAME)
            if matched is None
            else attached[matched.attachment_id()].policy_name
        )
        policy = self._policies_repo.get(name)
        if policy is None:
            raise NotFoundError(f"table maintenance policy {name.value} not found")
        return ResolveApplicableTableMaintenancePolicyUseCaseOutput(
            policy_name=name.value,
            version=policy.version,
            content=policy.content.to_primitives(),
            target=None if matched is None else _target_fields(matched),
        )

    def _candidates(self, request: ResolveApplicableTableMaintenancePolicyUseCaseInput) -> tuple[PolicyTarget, ...]:
        if request.table is None:
            return enclosing_policy_targets(request.catalog, request.namespace)
        if request.namespace is None:
            raise ValidationError("a table needs its namespace")
        table_uuid = request.table_uuid
        if table_uuid is None:
            loaded = self._gateway.load_table(
                TableMetadataRef(catalog=request.catalog, namespace=request.namespace, table=request.table)
            )
            if loaded is None:
                raise NotFoundError(f"table {request.catalog}.{request.namespace}.{request.table} not found")
            table_uuid = loaded.table_uuid
        with translate_domain_errors():
            name = TableName(catalog=request.catalog, namespace=request.namespace, table=request.table)
            return candidate_policy_targets(name, table_uuid)


def _target_fields(target: PolicyTarget) -> dict[str, object]:
    fields: dict[str, object] = {"type": target.type.value, "path": list(target.path)}
    if target.table_uuid is not None:
        fields["table_uuid"] = target.table_uuid
    return fields
