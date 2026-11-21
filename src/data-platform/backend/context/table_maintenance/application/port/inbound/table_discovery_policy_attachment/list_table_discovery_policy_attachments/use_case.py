"""Define the ListTableDiscoveryPolicyAttachmentsUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_discovery_policy_attachment.list_table_discovery_policy_attachments.input import (  # noqa: E501
    ListTableDiscoveryPolicyAttachmentsUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy_attachment.list_table_discovery_policy_attachments.output import (  # noqa: E501
    ListTableDiscoveryPolicyAttachmentsUseCaseOutput,
)


class ListTableDiscoveryPolicyAttachmentsUseCase(
    UseCase[ListTableDiscoveryPolicyAttachmentsUseCaseInput, ListTableDiscoveryPolicyAttachmentsUseCaseOutput]
):
    """List a discovery policy's attachments."""

    @abstractmethod
    def execute(
        self, request: ListTableDiscoveryPolicyAttachmentsUseCaseInput
    ) -> ListTableDiscoveryPolicyAttachmentsUseCaseOutput:
        """List a discovery policy's attachments."""
