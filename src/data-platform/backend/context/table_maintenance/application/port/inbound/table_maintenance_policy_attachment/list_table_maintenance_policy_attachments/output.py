"""Define the ListTableMaintenancePolicyAttachmentsUseCaseOutput."""

from __future__ import annotations

from datetime import datetime

from base import UseCaseOutput


class ListTableMaintenancePolicyAttachmentsUseCaseOutput(UseCaseOutput):
    """Carry the listing."""

    class TableMaintenancePolicyAttachment(UseCaseOutput):
        """One attachment of the listing; ``orphaned`` when its target is no longer in the catalog.

        ``id`` is the attachment's ``pa-`` id, ``policy_id`` the attached policy and ``policy_name`` its
        current name.
        """

        id: str
        type: str
        path: tuple[str, ...]
        table_uuid: str | None
        policy_id: str
        policy_name: str
        attached_at: datetime
        orphaned: bool

    items: tuple[TableMaintenancePolicyAttachment, ...]
