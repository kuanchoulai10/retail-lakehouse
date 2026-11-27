"""Define the GetTableDiscoveryPolicyVersionService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table_discovery_policy import (
    TableDiscoveryPolicyName,
)
from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table_discovery_policy import (
    GetTableDiscoveryPolicyVersionUseCase,
    GetTableDiscoveryPolicyVersionUseCaseInput,
    GetTableDiscoveryPolicyVersionUseCaseOutput,
)
from context.table_maintenance.application.service.shared import (
    translate_domain_errors,
)
from context.table_maintenance.application.service.table_discovery_policy.discovery_rule_fields import (
    discovery_rule_fields,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table_discovery_policy import (
        TableDiscoveryPoliciesRepo,
    )


class GetTableDiscoveryPolicyVersionService(GetTableDiscoveryPolicyVersionUseCase):
    """Get one stored version of a discovery policy."""

    def __init__(self, policies_repo: TableDiscoveryPoliciesRepo) -> None:
        """Bind the repo."""
        self._policies_repo = policies_repo

    def execute(
        self, request: GetTableDiscoveryPolicyVersionUseCaseInput
    ) -> GetTableDiscoveryPolicyVersionUseCaseOutput:
        """Return the version or raise NotFoundError."""
        with translate_domain_errors():
            name = TableDiscoveryPolicyName(value=request.name)
        policy = self._policies_repo.get_by_name(name)
        version = None if policy is None else self._policies_repo.get_version(policy.id, request.version)
        if policy is None or version is None:
            raise NotFoundError(f"discovery policy {request.name} has no version {request.version}")
        return GetTableDiscoveryPolicyVersionUseCaseOutput(
            id=policy.id.value,
            name=policy.name.value,
            version=version.version,
            description=version.description,
            rules=discovery_rule_fields(version.rules),
            created_at=version.created_at,
        )
