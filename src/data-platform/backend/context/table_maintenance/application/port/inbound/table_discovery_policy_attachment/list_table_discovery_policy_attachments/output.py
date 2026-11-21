"""Define the ListTableDiscoveryPolicyAttachmentsUseCaseOutput."""

from __future__ import annotations

from datetime import datetime

from base import UseCaseOutput


class ListTableDiscoveryPolicyAttachmentsUseCaseOutput(UseCaseOutput):
    """Carry the listing."""

    class TableDiscoveryPolicyAttachment(UseCaseOutput):
        """One attachment; ``orphaned`` when its target no longer exists in the catalog.

        A target in a catalog the platform's credential cannot read is not known to be gone, so it is
        not orphaned.
        """

        id: str
        type: str
        path: tuple[str, ...]
        table_uuid: str | None
        policy_id: str
        policy_name: str
        attached_at: datetime
        orphaned: bool

    items: tuple[TableDiscoveryPolicyAttachment, ...]
