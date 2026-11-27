"""Define the DeleteTableDiscoveryPolicyService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table_discovery_policy import (
    TableDiscoveryPolicyName,
)
from context.table_maintenance.application.exceptions import (
    ConflictError,
    NotFoundError,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy import (
    DeleteTableDiscoveryPolicyUseCase,
    DeleteTableDiscoveryPolicyUseCaseInput,
    DeleteTableDiscoveryPolicyUseCaseOutput,
)
from context.table_maintenance.application.service.shared import (
    translate_domain_errors,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table_discovery_policy import (
        TableDiscoveryPoliciesRepo,
    )
    from context.table_maintenance.application.port.outbound.table_discovery_policy_attachment import (
        TableDiscoveryPolicyAttachmentsRepo,
    )


class DeleteTableDiscoveryPolicyService(DeleteTableDiscoveryPolicyUseCase):
    """Delete a discovery policy that is not attached anywhere."""

    def __init__(
        self,
        policies_repo: TableDiscoveryPoliciesRepo,
        attachments_repo: TableDiscoveryPolicyAttachmentsRepo,
    ) -> None:
        """Bind the repos."""
        self._policies_repo = policies_repo
        self._attachments_repo = attachments_repo

    def execute(self, request: DeleteTableDiscoveryPolicyUseCaseInput) -> DeleteTableDiscoveryPolicyUseCaseOutput:
        """Delete the policy and its versions, refusing one that has attachments."""
        with translate_domain_errors():
            name = TableDiscoveryPolicyName(value=request.name)
        policy = self._policies_repo.get_by_name(name)
        if policy is None:
            raise NotFoundError(f"discovery policy {request.name} not found")
        if self._attachments_repo.has_attachments_for_policy(policy.id):
            raise ConflictError(f"discovery policy {name.value} is still attached to a catalog, namespace or table")
        self._policies_repo.delete(policy.id)
        return DeleteTableDiscoveryPolicyUseCaseOutput()
