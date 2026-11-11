"""Define the TableMaintenancePolicyAttachmentsRepo outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base import Repository
from context.table_maintenance.application.domain.model.table_maintenance_policy_attachment import (
    TableMaintenancePolicyAttachment,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from base import EntityId
    from context.table_maintenance.application.domain.model.table_maintenance_policy import (
        TableMaintenancePolicyName,
    )


class TableMaintenancePolicyAttachmentsRepo(Repository[TableMaintenancePolicyAttachment]):
    """Persist and query TableMaintenancePolicyAttachment aggregates."""

    @abstractmethod
    def update(self, attachment: TableMaintenancePolicyAttachment) -> TableMaintenancePolicyAttachment:
        """Persist the attachment's new policy."""

    @abstractmethod
    def delete(self, entity_id: EntityId) -> None:
        """Delete the attachment if present."""

    @abstractmethod
    def get_many(self, ids: Sequence[EntityId]) -> list[TableMaintenancePolicyAttachment]:
        """Return the attachments that exist among ``ids``, in no particular order."""

    @abstractmethod
    def list_for_policy(self, policy_name: TableMaintenancePolicyName) -> list[TableMaintenancePolicyAttachment]:
        """Return the attachments of one policy."""

    @abstractmethod
    def has_attachments_for_policy(self, policy_name: TableMaintenancePolicyName) -> bool:
        """Return whether any target uses the policy."""
