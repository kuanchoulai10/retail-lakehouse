"""Define the GetTableDiscoveryPolicyService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table_discovery_policy import (
    TableDiscoveryPolicyName,
)
from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table_discovery_policy import (
    GetTableDiscoveryPolicyUseCase,
    GetTableDiscoveryPolicyUseCaseInput,
    GetTableDiscoveryPolicyUseCaseOutput,
)
from context.table_maintenance.application.service.shared import (
    translate_domain_errors,
)
from context.table_maintenance.application.service.table_discovery_policy.table_discovery_policy_output_fields import (  # noqa: E501
    table_discovery_policy_output_fields,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table_discovery_policy import (
        TableDiscoveryPoliciesRepo,
    )


class GetTableDiscoveryPolicyService(GetTableDiscoveryPolicyUseCase):
    """Get the current version of one discovery policy."""

    def __init__(self, policies_repo: TableDiscoveryPoliciesRepo) -> None:
        """Bind the repo."""
        self._policies_repo = policies_repo

    def execute(self, request: GetTableDiscoveryPolicyUseCaseInput) -> GetTableDiscoveryPolicyUseCaseOutput:
        """Return the policy or raise NotFoundError."""
        with translate_domain_errors():
            name = TableDiscoveryPolicyName(value=request.name)
        policy = self._policies_repo.get_by_name(name)
        if policy is None:
            raise NotFoundError(f"discovery policy {request.name} not found")
        return GetTableDiscoveryPolicyUseCaseOutput(**table_discovery_policy_output_fields(policy))
