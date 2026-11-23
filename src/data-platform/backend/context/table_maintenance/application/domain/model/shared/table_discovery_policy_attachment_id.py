"""Define the TableDiscoveryPolicyAttachmentId identifier."""

from __future__ import annotations

from typing import ClassVar

from base import EntityId


class TableDiscoveryPolicyAttachmentId(EntityId):
    """Identify a discovery attachment: a random ``da-`` id issued when the attachment is first made (docs/adr/0011).

    The id says nothing about the target; a target's attachment is found by ``PolicyTarget.key()``.
    """

    PREFIX: ClassVar[str | None] = "da"
