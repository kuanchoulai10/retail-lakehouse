"""Define the TableDiscoveryPolicyAttachmentsRepo outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base import Repository
from context.table_maintenance.application.domain.model.table_discovery_policy_attachment import (
    TableDiscoveryPolicyAttachment,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from base import EntityId
    from context.table_maintenance.application.domain.model.shared import PolicyTarget, TableDiscoveryPolicyId


class TableDiscoveryPolicyAttachmentsRepo(Repository[TableDiscoveryPolicyAttachment]):
    """Persist and query TableDiscoveryPolicyAttachment aggregates.

    A target has at most one discovery attachment: ``create`` of a second one on the same
    ``PolicyTarget.key()`` raises ConflictError, whatever its id. Each attachment is stored with its
    catalog, so a scan reads only its own catalog's attachments.
    """

    @abstractmethod
    def get_by_target(self, target: PolicyTarget) -> TableDiscoveryPolicyAttachment | None:
        """Return the attachment on the target (matched by ``target.key()``), or None."""

    @abstractmethod
    def get_many_by_targets(self, targets: Sequence[PolicyTarget]) -> list[TableDiscoveryPolicyAttachment]:
        """Return the attachments on any of ``targets`` (matched by key), in no particular order."""

    @abstractmethod
    def list_in_catalog(self, catalog: str) -> list[TableDiscoveryPolicyAttachment]:
        """Return the attachments whose target is in ``catalog``: the catalog, its namespaces and its tables."""

    @abstractmethod
    def list_all(self) -> list[TableDiscoveryPolicyAttachment]:
        """Return every attachment, from which the scanned catalogs are worked out."""

    @abstractmethod
    def list_for_policy(self, policy_id: TableDiscoveryPolicyId) -> list[TableDiscoveryPolicyAttachment]:
        """Return the attachments of one policy."""

    @abstractmethod
    def has_attachments_for_policy(self, policy_id: TableDiscoveryPolicyId) -> bool:
        """Return whether any target uses the policy."""

    @abstractmethod
    def update(self, attachment: TableDiscoveryPolicyAttachment) -> TableDiscoveryPolicyAttachment:
        """Persist the attachment's new policy."""

    @abstractmethod
    def delete(self, entity_id: EntityId) -> None:
        """Delete the attachment if present."""
