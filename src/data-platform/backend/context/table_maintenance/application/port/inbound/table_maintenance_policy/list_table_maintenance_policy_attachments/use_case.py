"""Define the ListTableMaintenancePolicyAttachmentsUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_maintenance_policy.list_table_maintenance_policy_attachments.input import (  # noqa: E501
    ListTableMaintenancePolicyAttachmentsUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_policy.list_table_maintenance_policy_attachments.output import (  # noqa: E501
    ListTableMaintenancePolicyAttachmentsUseCaseOutput,
)


class ListTableMaintenancePolicyAttachmentsUseCase(
    UseCase[ListTableMaintenancePolicyAttachmentsUseCaseInput, ListTableMaintenancePolicyAttachmentsUseCaseOutput]
):
    """List the places one maintenance policy is attached to."""

    @abstractmethod
    def execute(
        self, request: ListTableMaintenancePolicyAttachmentsUseCaseInput
    ) -> ListTableMaintenancePolicyAttachmentsUseCaseOutput:
        """List the places one maintenance policy is attached to."""
