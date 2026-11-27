"""Define the ListTableDiscoveryPoliciesService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.port.inbound.table_discovery_policy import (
    ListTableDiscoveryPoliciesUseCase,
    ListTableDiscoveryPoliciesUseCaseInput,
    ListTableDiscoveryPoliciesUseCaseOutput,
)
from context.table_maintenance.application.service.table_discovery_policy.table_discovery_policy_output_fields import (  # noqa: E501
    table_discovery_policy_output_fields,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table_discovery_policy import (
        TableDiscoveryPoliciesRepo,
    )
    from context.table_maintenance.application.port.outbound.table_discovery_policy_attachment import (
        TableDiscoveryPolicyAttachmentsRepo,
    )


class ListTableDiscoveryPoliciesService(ListTableDiscoveryPoliciesUseCase):
    """List all discovery policies, each with how many targets it is attached to."""

    def __init__(
        self, policies_repo: TableDiscoveryPoliciesRepo, attachments_repo: TableDiscoveryPolicyAttachmentsRepo
    ) -> None:
        """Bind the repos."""
        self._policies_repo = policies_repo
        self._attachments_repo = attachments_repo

    def execute(
        self,
        request: ListTableDiscoveryPoliciesUseCaseInput,  # noqa: ARG002
    ) -> ListTableDiscoveryPoliciesUseCaseOutput:
        """Return every policy at its current version with its attachment count, by name."""
        policies = sorted(self._policies_repo.list_all(), key=lambda p: p.name.value)
        return ListTableDiscoveryPoliciesUseCaseOutput(
            items=tuple(
                ListTableDiscoveryPoliciesUseCaseOutput.TableDiscoveryPolicy(
                    **table_discovery_policy_output_fields(p),
                    attachment_count=len(self._attachments_repo.list_for_policy(p.id)),
                )
                for p in policies
            )
        )
