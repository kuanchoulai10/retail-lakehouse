"""Define the TableMaintenancePolicyAttachmentId identifier."""

from __future__ import annotations

from typing import ClassVar

from base import EntityId


class TableMaintenancePolicyAttachmentId(EntityId):
    """Identify an attachment: a random ``pa-`` id minted when the attachment is first made (docs/adr/0011).

    The id says nothing about the target; a target's attachment is found by ``PolicyTarget.key()``.
    """

    PREFIX: ClassVar[str | None] = "pa"
