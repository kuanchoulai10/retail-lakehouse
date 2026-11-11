"""Define the TableMaintenancePolicyAttachmentId identifier."""

from __future__ import annotations

from base import EntityId


class TableMaintenancePolicyAttachmentId(EntityId):
    """Identify an attachment by its target: ``table:<uuid>`` or ``<type>:<path>``."""
