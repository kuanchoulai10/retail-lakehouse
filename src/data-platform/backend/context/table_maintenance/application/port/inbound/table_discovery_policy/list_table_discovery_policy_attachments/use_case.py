"""Define the ListTableDiscoveryPolicyAttachmentsUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_discovery_policy.list_table_discovery_policy_attachments.input import (  # noqa: E501
    ListTableDiscoveryPolicyAttachmentsUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy.list_table_discovery_policy_attachments.output import (  # noqa: E501
    ListTableDiscoveryPolicyAttachmentsUseCaseOutput,
)


class ListTableDiscoveryPolicyAttachmentsUseCase(
    UseCase[ListTableDiscoveryPolicyAttachmentsUseCaseInput, ListTableDiscoveryPolicyAttachmentsUseCaseOutput]
):
    """List the places a discovery policy is attached to."""

    @abstractmethod
    def execute(
        self, request: ListTableDiscoveryPolicyAttachmentsUseCaseInput
    ) -> ListTableDiscoveryPolicyAttachmentsUseCaseOutput:
        """List the places a discovery policy is attached to."""
